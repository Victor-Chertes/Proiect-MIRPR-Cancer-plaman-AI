"""Build the small NSCLC Radiogenomics dataset used for training.

For every patient that has an expert tumor segmentation on CT and a known EGFR or
KRAS status, download the CT series and its DICOM SEG from the Imaging Data
Commons, convert them to NIfTI, resample to 1 mm isotropic and save a cube
centred on the tumor. Raw DICOM is deleted after each patient.

With --extend (stage 3) the dataset grows to every labelled patient that has a
tumor segmentation. Patients without an expert CT segmentation get the IDC
"AIMI lung and FDG tumor" AI segmentation, which is drawn on the PET of the same
PET/CT study. That mask is projected onto the PET/CT's CT (same frame of
reference); of its connected components we keep the largest one lying mostly
inside the lung, and drop voxels below -700 HU (the PET mask is coarser than CT).

Output (data/):
  selection.csv          which CT/SEG series were picked per patient
  labels.csv             one row per patient: clinical fields + labels
  crops/<id>_ct.nii.gz   96 mm cube of CT (HU, int16), 1 mm spacing
  crops/<id>_mask.nii.gz the tumor mask on the same grid (uint8)
  full/<id>_*.nii.gz     whole CT + mask for a few patients (app demo input)

Usage: python prepare_dataset.py [--demo 5] [--limit N] [--extend]
"""

import argparse
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pydicom
import SimpleITK as sitk
from idc_index import IDCClient
from scipy import ndimage

ROOT = Path(__file__).parent / "data"
CROP_MM = 96
CLINICAL = "nsclc_radiogenomics_clinical"
# AI PET masks rejected after visual review of every --extend crop (eda3_qa.png)
QA_REJECTED = {
    "R01-160": "mask lies in the upper abdomen, not in the lung",
    "R01-149": "mask lies on paravertebral soft tissue outside the lung",
}


def select_series(client: IDCClient) -> pd.DataFrame:
    client.fetch_index("seg_index")
    df = client.sql_query(
        """
        select i.PatientID, s.SeriesInstanceUID seg_uid, i.SeriesDescription seg_desc,
               s.segmented_SeriesInstanceUID ct_uid, r.series_size_MB ct_mb
        from seg_index s
        join index i using (SeriesInstanceUID)
        join index r on r.SeriesInstanceUID = s.segmented_SeriesInstanceUID
        where i.collection_id = 'nsclc_radiogenomics' and r.Modality = 'CT'
          and (i.SeriesDescription like '3D Slicer%' or i.SeriesDescription like 'ePAD%')
        """
    )
    df = df.sort_values(["PatientID", "seg_desc"]).drop_duplicates("PatientID")
    df["mask_source"] = "expert"
    return df


def select_pet_series(client: IDCClient, exclude: set) -> pd.DataFrame:
    """AI PET tumor segmentation + the CT of the same PET/CT study, for the other patients."""
    df = client.sql_query(
        """
        select i.PatientID, s.SeriesInstanceUID seg_uid, i.SeriesDescription seg_desc,
               s.segmented_SeriesInstanceUID pet_uid, c.SeriesInstanceUID ct_uid,
               c.series_size_MB ct_mb, c.instanceCount ct_slices
        from seg_index s
        join index i using (SeriesInstanceUID)
        join index p on p.SeriesInstanceUID = s.segmented_SeriesInstanceUID
        join index c on c.StudyInstanceUID = p.StudyInstanceUID and c.Modality = 'CT'
        where i.collection_id = 'nsclc_radiogenomics' and p.Modality = 'PT'
          and i.SeriesDescription like 'AIMI lung and FDG tumor%'
        """
    )
    df = df[~df.PatientID.isin(exclude)]
    # prefer a radiologist-corrected mask over the raw AI one, and the CT with most slices
    df["corrected"] = df.seg_desc.str.contains("corrected")
    df = df.sort_values(["PatientID", "corrected", "ct_slices"], ascending=[True, False, False])
    df = df.drop_duplicates("PatientID").drop(columns=["corrected", "ct_slices"])
    df["mask_source"] = "ai_pet"
    return df


def load_clinical(client: IDCClient) -> pd.DataFrame:
    client.fetch_index("clinical_index")
    path = Path(client.clinical_data_dir) / CLINICAL
    return pd.read_parquet(next(path.glob("*.parquet")))


def binary(value: str, positive: str) -> float:
    if value == positive:
        return 1.0
    if value == "Wildtype":
        return 0.0
    return np.nan


def read_ct(folder: Path) -> sitk.Image:
    reader = sitk.ImageSeriesReader()
    files = reader.GetGDCMSeriesFileNames(str(folder))
    reader.SetFileNames(files)
    return reader.Execute()


def read_seg(seg_file: Path, ct: sitk.Image, label: str | None = None) -> sitk.Image:
    """Rasterise SEG frames onto the CT grid using their patient position.

    label: keep only segments whose label contains this text (default: all segments).
    """
    ds = pydicom.dcmread(seg_file)
    frames = ds.pixel_array
    if frames.ndim == 2:
        frames = frames[None]
    keep = {s.SegmentNumber for s in ds.SegmentSequence
            if label is None or label.lower() in s.SegmentLabel.lower()}
    mask = np.zeros(sitk.GetArrayFromImage(ct).shape, dtype=np.uint8)
    for frame, group in zip(frames, ds.PerFrameFunctionalGroupsSequence):
        if group.SegmentIdentificationSequence[0].ReferencedSegmentNumber not in keep:
            continue
        position = [float(v) for v in group.PlanePositionSequence[0].ImagePositionPatient]
        _, _, z = ct.TransformPhysicalPointToIndex(position)
        if 0 <= z < mask.shape[0] and frame.shape == mask.shape[1:]:
            mask[z] |= (frame > 0).astype(np.uint8)
    out = sitk.GetImageFromArray(mask)
    out.CopyInformation(ct)
    return out


def pet_tumor_on_ct(seg_file: Path, pet: sitk.Image, ct: sitk.Image) -> sitk.Image:
    """Project the PET-based tumor mask onto the CT and keep the primary lung tumor."""
    def on_ct(label):
        mask = read_seg(seg_file, pet, label)
        return sitk.GetArrayFromImage(
            sitk.Resample(mask, ct, sitk.Transform(), sitk.sitkNearestNeighbor, 0)) > 0

    tumor, lung = on_ct("tumor"), on_ct("lung")
    if not tumor.any():
        raise ValueError("the AI segmentation has no tumor")
    lung = ndimage.binary_dilation(lung, iterations=3)
    components, n = ndimage.label(tumor)
    best, best_size = 0, 0
    for k in range(1, n + 1):
        comp = components == k
        size = comp.sum()
        if (comp & lung).sum() >= 0.5 * size and size > best_size:
            best, best_size = k, size
    if not best:
        raise ValueError("no FDG-avid tumor inside the lung")
    hu = sitk.GetArrayFromImage(ct)
    out = sitk.GetImageFromArray(((components == best) & (hu > -700)).astype(np.uint8))
    out.CopyInformation(ct)
    return out


def around_tumor(ct: sitk.Image, mask: sitk.Image, margin_mm: float):
    nz = np.argwhere(sitk.GetArrayViewFromImage(mask) > 0)[:, ::-1]  # x, y, z
    margin = np.ceil(margin_mm / np.array(ct.GetSpacing())).astype(int)
    low = np.maximum(nz.min(0) - margin, 0)
    high = np.minimum(nz.max(0) + margin + 1, ct.GetSize())
    size = [int(v) for v in high - low]
    index = [int(v) for v in low]
    return sitk.RegionOfInterest(ct, size, index), sitk.RegionOfInterest(mask, size, index)


def resample_iso(image: sitk.Image, interp, default: float) -> sitk.Image:
    spacing = image.GetSpacing()
    size = [int(round(n * s)) for n, s in zip(image.GetSize(), spacing)]
    return sitk.Resample(
        image, size, sitk.Transform(), interp, image.GetOrigin(), (1.0, 1.0, 1.0),
        image.GetDirection(), default, image.GetPixelID(),
    )


def crop_around_tumor(ct: sitk.Image, mask: sitk.Image):
    arr_ct = sitk.GetArrayFromImage(ct)
    arr_m = sitk.GetArrayFromImage(mask)
    centre = np.round(np.argwhere(arr_m > 0).mean(axis=0)).astype(int)
    half = CROP_MM // 2
    pad = [(half, half)] * 3
    arr_ct = np.pad(arr_ct, pad, constant_values=-1024)
    arr_m = np.pad(arr_m, pad, constant_values=0)
    sl = tuple(slice(c, c + CROP_MM) for c in centre)
    return arr_ct[sl].astype(np.int16), arr_m[sl].astype(np.uint8)


def save_nifti(arr: np.ndarray, path: Path) -> None:
    img = sitk.GetImageFromArray(arr)
    img.SetSpacing((1.0, 1.0, 1.0))
    sitk.WriteImage(img, str(path), useCompression=True)


def process(client: IDCClient, row, tmp: Path, crops: Path, full: Path | None) -> dict:
    target = tmp / row.PatientID
    pet_uid = getattr(row, "pet_uid", None)
    pet_uid = pet_uid if isinstance(pet_uid, str) else None
    client.download_from_selection(
        seriesInstanceUID=[row.ct_uid, row.seg_uid] + ([pet_uid] if pet_uid else []),
        downloadDir=str(target),
        dirTemplate="%SeriesInstanceUID",
        quiet=True,
        show_progress_bar=False,
    )
    ct = read_ct(target / row.ct_uid)
    seg_file = next((target / row.seg_uid).glob("*.dcm"))
    slices = ct.GetSize()[2]
    if pet_uid:
        mask = pet_tumor_on_ct(seg_file, read_ct(target / pet_uid), ct)
        # whole-body PET/CT is too large to resample whole: keep a margin around the tumor
        ct, mask = around_tumor(ct, mask, margin_mm=CROP_MM)
    else:
        mask = read_seg(seg_file, ct)
    if full is not None:
        sitk.WriteImage(ct, str(full / f"{row.PatientID}_ct.nii.gz"), useCompression=True)
        sitk.WriteImage(mask, str(full / f"{row.PatientID}_mask.nii.gz"), useCompression=True)

    spacing = ct.GetSpacing()
    voxels = int(sitk.GetArrayViewFromImage(mask).sum())
    ct_iso = resample_iso(ct, sitk.sitkLinear, -1024)
    mask_iso = resample_iso(mask, sitk.sitkNearestNeighbor, 0)
    arr_ct, arr_m = crop_around_tumor(ct_iso, mask_iso)
    save_nifti(arr_ct, crops / f"{row.PatientID}_ct.nii.gz")
    save_nifti(arr_m, crops / f"{row.PatientID}_mask.nii.gz")
    shutil.rmtree(target, ignore_errors=True)
    return {
        "patient_id": row.PatientID,
        "spacing_x": spacing[0],
        "spacing_z": spacing[2],
        "tumor_volume_ml": voxels * np.prod(spacing) / 1000,
        "tumor_in_crop": int(arr_m.sum()),
        "slices": slices,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", type=int, default=5, help="patients to also keep as full NIfTI")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--extend", action="store_true",
                        help="also add patients that only have the AI PET tumor segmentation")
    args = parser.parse_args()

    crops, full, tmp = ROOT / "crops", ROOT / "full", ROOT / "tmp"
    for d in (crops, full, tmp):
        d.mkdir(parents=True, exist_ok=True)

    client = IDCClient()
    clinical = load_clinical(client)
    selection = select_series(client)
    if args.extend:
        selection = pd.concat([selection, select_pet_series(client, set(selection.PatientID))])
    selection = selection.merge(clinical, left_on="PatientID", right_on="dicom_patient_id")
    selection["egfr"] = selection.egfr_mutation_status.map(lambda v: binary(v, "Mutant"))
    selection["kras"] = selection.kras_mutation_status.map(lambda v: binary(v, "Mutant"))
    selection["alk"] = selection.alk_translocation_status.map(lambda v: binary(v, "Translocated"))
    selection = selection[selection.egfr.notna() | selection.kras.notna()].reset_index(drop=True)
    if args.limit:
        selection = selection.head(args.limit)
    if "pet_uid" not in selection:
        selection["pet_uid"] = np.nan
    selection[["PatientID", "mask_source", "seg_uid", "seg_desc", "ct_uid", "pet_uid", "ct_mb"]].to_csv(
        ROOT / "selection.csv", index=False
    )
    print(f"{len(selection)} patients, {selection.ct_mb.sum() / 1024:.1f} GB of CT to fetch")

    done_path = ROOT / "image_meta.csv"
    done = pd.read_csv(done_path) if done_path.exists() else pd.DataFrame()
    finished = set(done.get("patient_id", []))
    rows = done.to_dict("records")
    for i, row in enumerate(selection.itertuples()):
        if row.PatientID in finished:
            continue
        try:
            meta = process(client, row, tmp, crops, full if i < args.demo else None)
            rows.append(meta)
            pd.DataFrame(rows).to_csv(done_path, index=False)
            print(f"[{i + 1}/{len(selection)}] {row.PatientID} ok "
                  f"tumor {meta['tumor_volume_ml']:.1f} ml", flush=True)
        except Exception as exc:
            print(f"[{i + 1}/{len(selection)}] {row.PatientID} FAILED: {exc}", flush=True)
            shutil.rmtree(tmp / row.PatientID, ignore_errors=True)

    meta = pd.DataFrame(rows)
    labels = selection.rename(columns={"PatientID": "patient_id"})[
        ["patient_id", "age_at_histological_diagnosis", "gender", "smoking_status",
         "histology", "pathological_t_stage", "egfr", "kras", "alk", "mask_source"]
    ].rename(columns={"age_at_histological_diagnosis": "age", "gender": "sex"})
    labels["sex"] = labels.sex.map({"Male": "M", "Female": "F"})
    labels = labels.merge(meta, on="patient_id")
    labels = labels[~labels.patient_id.isin(QA_REJECTED)]
    labels.to_csv(ROOT / "labels.csv", index=False)
    print(f"labels.csv: {len(labels)} patients with crops")


if __name__ == "__main__":
    main()

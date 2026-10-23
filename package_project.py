"""Package code, SO-101 model with license, video and report."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent


def main(account):
    report = ROOT / f"説明資料_PAI最終課題_{account}.pdf"
    if not report.is_file():
        raise FileNotFoundError("build_report.py --account で先にPDFを作成してください")
    files = list(ROOT.glob("*.py")) + list(ROOT.glob("*.bat")) + list(ROOT.glob("*.sh"))
    files += [ROOT / n for n in ["requirements.txt", "requirements-lock.txt", "environment_versions.json", "README.md", "THIRD_PARTY.md", "提出手順.md", "YouTubeタイトル.txt", "YouTube概要欄.txt", ".gitignore", ".gitattributes"]]
    files += [p for folder in ["assets", "models"] for p in (ROOT / folder).rglob("*") if p.is_file()]
    files += [p for p in (ROOT / "outputs").iterdir() if p.is_file() and p.name in {
        "demo.mp4", "run_summary.json", "verification.json", "start.png", "simulation.png", "success.png",
        "camera_A.png", "camera_B.png", "camera_C.png", "video_contact_sheet.png"}]
    files += [report]
    alternate = ROOT / "outputs/check_alternate/run_summary.json"
    if alternate.is_file():
        files.append(alternate)
    with ZipFile(ROOT / "submission.zip", "w", ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, "genesis_ai_buttons/" + file.relative_to(ROOT).as_posix())
    print(f"submission.zip: {len(files)} files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", default="shirakashi")
    main(parser.parse_args().account)

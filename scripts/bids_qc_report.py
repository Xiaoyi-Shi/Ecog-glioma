from __future__ import annotations

import argparse
import base64
import html
import io
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import welch

_MNE_HOME = tempfile.mkdtemp(prefix="mne-home-")
os.environ.setdefault("MNE_HOME", _MNE_HOME)

import atexit

import mne


atexit.register(lambda: shutil.rmtree(_MNE_HOME, ignore_errors=True))


DEFAULT_BIDS_ROOT = Path("datas/data_02_BIDS")
DEFAULT_OUTPUT_DIR = Path("results")
DATA_EXTENSIONS = (".edf", ".vhdr", ".fif", ".set", ".bdf")
DATA_SUFFIXES = ("ieeg", "eeg", "meg", "nirs")


@dataclass
class BadSegment:
    onset: float
    duration: float

    @property
    def end(self) -> float:
        return self.onset + self.duration


@dataclass
class RecordingQC:
    subject: str
    session: str
    task: str
    run: str
    datatype: str
    recording_path: Path
    total_channels: int
    bad_channels: list[str]
    bad_segments: list[BadSegment]
    sfreq: float
    duration_seconds: float
    psd_image_base64: str

    @property
    def good_channel_count(self) -> int:
        return self.total_channels - len(self.bad_channels)

    @property
    def total_bad_duration(self) -> float:
        return sum(segment.duration for segment in self.bad_segments)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a simple HTML QC overview for a BIDS electrophysiology dataset. "
            "The dataset is read-only; the script only writes one HTML report to results."
        )
    )
    parser.add_argument(
        "--bids-root",
        type=Path,
        default=DEFAULT_BIDS_ROOT,
        help="BIDS root directory to inspect.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory that will receive the dated HTML report.",
    )
    parser.add_argument(
        "--fmin",
        type=float,
        default=1.0,
        help="Lower PSD frequency bound in Hz.",
    )
    parser.add_argument(
        "--fmax",
        type=float,
        default=200.0,
        help="Upper PSD frequency bound in Hz.",
    )
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def as_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else repo_root() / path


def resolve_recording_file(channels_tsv: Path) -> tuple[Path, str]:
    stem = channels_tsv.stem.removesuffix("_channels")
    for suffix in DATA_SUFFIXES:
        for extension in DATA_EXTENSIONS:
            candidate = channels_tsv.with_name(f"{stem}_{suffix}{extension}")
            if candidate.exists():
                return candidate, suffix
    raise FileNotFoundError(f"No recording file found next to {channels_tsv.name}")


def parse_entities(path: Path) -> tuple[str, str, str, str]:
    parts = path.stem.split("_")
    entities: dict[str, str] = {}
    for part in parts:
        if "-" in part:
            key, value = part.split("-", maxsplit=1)
            entities[key] = value
    subject = entities.get("sub", "unknown")
    session = entities.get("ses", "unknown")
    task = entities.get("task", "unknown")
    run = entities.get("run", "unknown")
    return subject, session, task, run


def load_channels(channels_tsv: Path) -> tuple[int, list[str]]:
    channels = pd.read_csv(channels_tsv, sep="\t")
    status = channels["status"].fillna("good").astype(str).str.lower()
    bad_mask = status == "bad"
    bad_channels = channels.loc[bad_mask, "name"].astype(str).tolist()
    return len(channels), bad_channels


def load_bad_segments(events_tsv: Path) -> list[BadSegment]:
    if not events_tsv.exists():
        return []

    events = pd.read_csv(events_tsv, sep="\t")
    if "trial_type" not in events.columns:
        return []

    bad_events = events.loc[
        events["trial_type"].fillna("").astype(str).str.lower().str.contains("bad"),
        ["onset", "duration"],
    ]
    segments = [
        BadSegment(onset=float(row.onset), duration=float(row.duration))
        for row in bad_events.itertuples(index=False)
    ]
    return segments


def compute_psd_plot(
    recording_path: Path,
    bad_channels: list[str],
    fmin: float,
    fmax: float,
    bad_segments: list[BadSegment],
) -> tuple[str, float, float]:
    raw = mne.io.read_raw(recording_path, preload=True, verbose="ERROR")
    raw.info["bads"] = bad_channels

    sfreq = float(raw.info["sfreq"])
    duration_seconds = float(raw.n_times / sfreq)
    data = raw.get_data()
    nperseg = min(4096, data.shape[1])
    noverlap = nperseg // 2

    freqs, psd = welch(
        data,
        fs=sfreq,
        nperseg=nperseg,
        noverlap=noverlap,
        axis=1,
    )
    freq_mask = (freqs >= fmin) & (freqs <= fmax)
    freqs = freqs[freq_mask]
    psd = psd[:, freq_mask]

    good_indices = [index for index, name in enumerate(raw.ch_names) if name not in bad_channels]
    bad_indices = [index for index, name in enumerate(raw.ch_names) if name in bad_channels]
    good_psd = psd[good_indices] if good_indices else np.empty((0, len(freqs)))
    bad_psd = psd[bad_indices] if bad_indices else np.empty((0, len(freqs)))

    fig, (ax_psd, ax_timeline) = plt.subplots(
        nrows=2,
        figsize=(10, 6),
        gridspec_kw={"height_ratios": [3.0, 1.0]},
        constrained_layout=True,
    )

    if good_psd.size:
        for row in good_psd:
            ax_psd.plot(freqs, row, color="#8fb8de", alpha=0.18, linewidth=0.6)
        ax_psd.plot(
            freqs,
            good_psd.mean(axis=0),
            color="#0b5394",
            linewidth=2.0,
            label=f"Good channels mean (n={len(good_indices)})",
        )
    if bad_psd.size:
        ax_psd.plot(
            freqs,
            bad_psd.mean(axis=0),
            color="#c0392b",
            linewidth=1.6,
            linestyle="--",
            label=f"Bad channels mean (n={len(bad_indices)})",
        )

    ax_psd.set_yscale("log")
    ax_psd.set_xlabel("Frequency (Hz)")
    ax_psd.set_ylabel("PSD")
    ax_psd.set_title(recording_path.name)
    ax_psd.grid(True, alpha=0.25)
    if ax_psd.lines:
        ax_psd.legend(loc="upper right", frameon=False)

    ax_timeline.set_xlim(0, duration_seconds)
    ax_timeline.set_ylim(0, 1)
    ax_timeline.set_yticks([])
    ax_timeline.set_xlabel("Time (s)")
    ax_timeline.set_title("Bad segments timeline")
    ax_timeline.axhspan(0.2, 0.8, color="#d9ead3", alpha=0.8)

    for segment in bad_segments:
        ax_timeline.broken_barh(
            [(segment.onset, segment.duration)],
            (0.2, 0.6),
            facecolors="#cc0000",
            alpha=0.85,
        )

    if not bad_segments:
        ax_timeline.text(
            0.5,
            0.5,
            "No bad segments",
            ha="center",
            va="center",
            transform=ax_timeline.transAxes,
            color="#555555",
        )

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=140)
    plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return encoded, sfreq, duration_seconds


def collect_recordings(bids_root: Path, fmin: float, fmax: float) -> list[RecordingQC]:
    recordings: list[RecordingQC] = []
    for channels_tsv in sorted(bids_root.rglob("*_channels.tsv")):
        recording_path, datatype = resolve_recording_file(channels_tsv)
        events_tsv = channels_tsv.with_name(channels_tsv.name.replace("_channels.tsv", "_events.tsv"))
        total_channels, bad_channels = load_channels(channels_tsv)
        bad_segments = load_bad_segments(events_tsv)
        psd_image_base64, sfreq, duration_seconds = compute_psd_plot(
            recording_path=recording_path,
            bad_channels=bad_channels,
            fmin=fmin,
            fmax=fmax,
            bad_segments=bad_segments,
        )
        subject, session, task, run = parse_entities(recording_path)
        recordings.append(
            RecordingQC(
                subject=subject,
                session=session,
                task=task,
                run=run,
                datatype=datatype,
                recording_path=recording_path,
                total_channels=total_channels,
                bad_channels=bad_channels,
                bad_segments=bad_segments,
                sfreq=sfreq,
                duration_seconds=duration_seconds,
                psd_image_base64=psd_image_base64,
            )
        )
    return recordings


def format_seconds(value: float) -> str:
    return f"{value:.2f}"


def make_summary_table(recordings: list[RecordingQC]) -> pd.DataFrame:
    rows = []
    for record in recordings:
        rows.append(
            {
                "subject": record.subject,
                "session": record.session,
                "task": record.task,
                "run": record.run,
                "datatype": record.datatype,
                "channels_total": record.total_channels,
                "channels_bad": len(record.bad_channels),
                "channels_good": record.good_channel_count,
                "bad_segments": len(record.bad_segments),
                "bad_duration_s": round(record.total_bad_duration, 3),
                "sfreq_hz": round(record.sfreq, 3),
                "duration_s": round(record.duration_seconds, 3),
            }
        )
    return pd.DataFrame(rows)


def render_bad_segments_table(record: RecordingQC) -> str:
    if not record.bad_segments:
        return "<p class='muted'>No bad segments.</p>"

    rows = []
    for index, segment in enumerate(record.bad_segments, start=1):
        rows.append(
            {
                "segment": index,
                "onset_s": round(segment.onset, 3),
                "duration_s": round(segment.duration, 3),
                "end_s": round(segment.end, 3),
            }
        )
    return pd.DataFrame(rows).to_html(index=False, classes="table", border=0)


def render_recording_section(record: RecordingQC) -> str:
    bad_channels_display = ", ".join(record.bad_channels) if record.bad_channels else "None"
    anchor = f"sub-{record.subject}-ses-{record.session}-run-{record.run}"
    return f"""
    <section class="record-card" id="{html.escape(anchor)}">
      <h2>sub-{html.escape(record.subject)} | ses-{html.escape(record.session)} | run-{html.escape(record.run)}</h2>
      <p class="meta">
        file: <code>{html.escape(str(record.recording_path.relative_to(repo_root())))}</code><br>
        datatype: <code>{html.escape(record.datatype)}</code> |
        task: <code>{html.escape(record.task)}</code> |
        sfreq: <code>{record.sfreq:.2f} Hz</code> |
        duration: <code>{record.duration_seconds:.2f} s</code>
      </p>
      <div class="stats">
        <div class="stat-box"><span class="stat-label">Bad channels</span><span class="stat-value">{len(record.bad_channels)}</span></div>
        <div class="stat-box"><span class="stat-label">Good channels</span><span class="stat-value">{record.good_channel_count}</span></div>
        <div class="stat-box"><span class="stat-label">Bad segments</span><span class="stat-value">{len(record.bad_segments)}</span></div>
        <div class="stat-box"><span class="stat-label">Bad duration</span><span class="stat-value">{record.total_bad_duration:.2f}s</span></div>
      </div>
      <p><strong>Bad channel list:</strong> {html.escape(bad_channels_display)}</p>
      <div class="figure-wrap">
        <img alt="PSD overview for sub-{html.escape(record.subject)} run-{html.escape(record.run)}" src="data:image/png;base64,{record.psd_image_base64}">
      </div>
      <h3>Bad segment positions</h3>
      {render_bad_segments_table(record)}
    </section>
    """


def build_html_report(recordings: list[RecordingQC], bids_root: Path, fmin: float, fmax: float) -> str:
    summary = make_summary_table(recordings)
    total_bad_channels = int(summary["channels_bad"].sum()) if not summary.empty else 0
    recordings_with_bad_segments = int((summary["bad_segments"] > 0).sum()) if not summary.empty else 0
    total_bad_duration = float(summary["bad_duration_s"].sum()) if not summary.empty else 0.0
    summary_html = summary.to_html(index=False, classes="table summary-table", border=0)
    recording_links = "\n".join(
        f"<li><a href='#{html.escape(f'sub-{record.subject}-ses-{record.session}-run-{record.run}')}'>"
        f"sub-{html.escape(record.subject)} / run-{html.escape(record.run)}</a></li>"
        for record in recordings
    )
    recording_sections = "\n".join(render_recording_section(record) for record in recordings)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BIDS QC Report</title>
  <style>
    :root {{
      --bg: #f6f5f1;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #6b7280;
      --line: #d9dee5;
      --accent: #0b5394;
      --accent-soft: #d9e9f7;
      --warn: #a61b1b;
      --good: #d9ead3;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      background: linear-gradient(180deg, #f3f1ea 0%, #faf9f6 100%);
      color: var(--ink);
      line-height: 1.5;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }}
    .hero {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 24px;
      box-shadow: 0 10px 30px rgba(31, 41, 51, 0.06);
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: 30px;
    }}
    .hero p {{
      margin: 4px 0;
      color: var(--muted);
    }}
    .top-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .top-card, .record-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 10px 30px rgba(31, 41, 51, 0.06);
    }}
    .top-card {{
      padding: 16px;
    }}
    .top-card .label {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .top-card .value {{
      font-size: 28px;
      font-weight: 700;
      color: var(--accent);
    }}
    .section-title {{
      margin: 28px 0 12px;
      font-size: 22px;
    }}
    .table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      overflow: hidden;
      border-radius: 12px;
    }}
    .table th, .table td {{
      border: 1px solid var(--line);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    .table th {{
      background: #eef4fb;
    }}
    .record-nav {{
      columns: 2 260px;
      padding-left: 18px;
    }}
    .record-card {{
      padding: 22px;
      margin-top: 22px;
    }}
    .record-card h2 {{
      margin-top: 0;
      margin-bottom: 8px;
      font-size: 24px;
    }}
    .record-card h3 {{
      margin-top: 20px;
      margin-bottom: 10px;
      font-size: 18px;
    }}
    .meta {{
      color: var(--muted);
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .stat-box {{
      border-radius: 14px;
      padding: 14px;
      background: linear-gradient(180deg, var(--accent-soft) 0%, #ffffff 100%);
      border: 1px solid #c9dff3;
    }}
    .stat-label {{
      display: block;
      font-size: 13px;
      color: var(--muted);
    }}
    .stat-value {{
      display: block;
      margin-top: 6px;
      font-size: 24px;
      font-weight: 700;
      color: var(--accent);
    }}
    .figure-wrap {{
      margin-top: 14px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fcfcfb;
    }}
    .figure-wrap img {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 10px;
    }}
    .muted {{
      color: var(--muted);
    }}
    code {{
      background: #f1f5f9;
      padding: 1px 5px;
      border-radius: 6px;
    }}
    @media (max-width: 720px) {{
      main {{
        padding: 18px 14px 48px;
      }}
      .hero h1 {{
        font-size: 24px;
      }}
      .record-nav {{
        columns: 1;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>BIDS QC Report</h1>
      <p>BIDS root: <code>{html.escape(str(bids_root.relative_to(repo_root())))}</code></p>
      <p>Generated at: <code>{html.escape(generated_at)}</code></p>
      <p>PSD range: <code>{fmin:.1f}-{fmax:.1f} Hz</code></p>
    </section>

    <section class="top-grid">
      <div class="top-card"><span class="label">Recordings</span><span class="value">{len(recordings)}</span></div>
      <div class="top-card"><span class="label">Total bad channels</span><span class="value">{total_bad_channels}</span></div>
      <div class="top-card"><span class="label">Recordings with bad segments</span><span class="value">{recordings_with_bad_segments}</span></div>
      <div class="top-card"><span class="label">Total bad duration</span><span class="value">{format_seconds(total_bad_duration)}s</span></div>
    </section>

    <h2 class="section-title">Dataset summary</h2>
    {summary_html}

    <h2 class="section-title">Recordings</h2>
    <ul class="record-nav">
      {recording_links}
    </ul>

    {recording_sections}
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    bids_root = as_repo_path(args.bids_root)
    output_dir = as_repo_path(args.output_dir)

    if not bids_root.exists():
        raise FileNotFoundError(f"BIDS root does not exist: {bids_root}")

    recordings = collect_recordings(
        bids_root=bids_root,
        fmin=args.fmin,
        fmax=args.fmax,
    )
    if not recordings:
        raise FileNotFoundError(f"No *_channels.tsv files found under {bids_root}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date.today().isoformat()}.html"
    report_html = build_html_report(
        recordings=recordings,
        bids_root=bids_root,
        fmin=args.fmin,
        fmax=args.fmax,
    )
    output_path.write_text(report_html, encoding="utf-8")

    print(f"Wrote QC report: {output_path}")
    print(f"Recordings inspected: {len(recordings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

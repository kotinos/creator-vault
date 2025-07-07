import csv
from dataclasses import dataclass, asdict
import os


@dataclass
class VisualSegmentAnalysis:
    """Holds the detailed analysis for a single visual segment of a video."""
    video_filename: str
    segment_id: str
    start_time: str
    end_time: str
    shot_type: str
    spoken_text: str
    visual_description: str
    inferred_purpose: str
    effectiveness_rating: int
    effectiveness_justification: str


def write_analysis_to_csv(analysis_results: list[VisualSegmentAnalysis],
                          csv_path: str):
    """Appends a list of VisualSegmentAnalysis objects to a CSV file."""
    if not analysis_results:
        print("No analysis results to write.")
        return

    fieldnames = list(asdict(analysis_results[0]).keys())
    file_exists = os.path.exists(csv_path)
    write_header = not file_exists or os.stat(csv_path).st_size == 0
    print(f"[CSV] Appending {len(analysis_results)} results to "
          f"{csv_path}")
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames,
                                    quoting=csv.QUOTE_ALL)
            if write_header:
                writer.writeheader()
            for result in analysis_results:
                row = asdict(result)
                writer.writerow(row)
        print(f"Analysis results appended to {csv_path}")
    except Exception as e:
        print(f"[CSV] Exception while appending to {csv_path}: {e}")


if __name__ == '__main__':
    # Example usage:
    sample_analysis = [
        VisualSegmentAnalysis(
            video_filename="example_video.mp4",
            segment_id="segment_1",
            start_time="00:00:00.000",
            end_time="00:00:15.500",
            shot_type="B-roll",
            spoken_text=("In this video, we'll explore the beautiful "
                         "mountains."),
            visual_description="A wide shot of a mountain range at "
                               "sunrise.",
            inferred_purpose="Establishes the setting and mood of the "
                             "video.",
            effectiveness_rating=5,
            effectiveness_justification=("Visually stunning and sets a "
                                         "clear context.")
        ),
        VisualSegmentAnalysis(
            video_filename="example_video.mp4",
            segment_id="segment_2",
            start_time="00:00:15.500",
            end_time="00:00:30.000",
            shot_type="Talking Head",
            spoken_text="The key is to use a variety of shots to keep "
                        "the viewer engaged.",
            visual_description="A medium shot of the presenter speaking "
                               "directly to the camera.",
            inferred_purpose="Creates a personal connection with the viewer.",
            effectiveness_rating=4,
            effectiveness_justification=("Direct address is engaging, "
                                         "but the background is a bit plain.")
        )
    ]

    write_analysis_to_csv(sample_analysis, "analysis_results.csv")

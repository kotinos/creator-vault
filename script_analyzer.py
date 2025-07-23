import csv
from dataclasses import dataclass, asdict
import os

@dataclass
class ScriptAnalysis:
    """Holds the detailed script analysis for a video."""
    video_filename: str
    overall_message: str
    script_purpose: str
    tonality: str
    emotional_arc: str
    hook_effectiveness: str
    narrative_flow: str
    transition_quality: str
    call_to_action: str
    recurring_patterns: str
    line_by_line_analysis: str
    effectiveness_score: str
    improvement_suggestions: str

def write_script_analysis_to_csv(analysis_results: list[ScriptAnalysis], csv_path: str):
    """Appends a list of ScriptAnalysis objects to a CSV file."""
    if not analysis_results:
        print("No script analysis results to write.")
        return

    fieldnames = list(asdict(analysis_results[0]).keys())
    file_exists = os.path.exists(csv_path)
    write_header = not file_exists or os.stat(csv_path).st_size == 0
    print(f"[SCRIPT CSV] Appending {len(analysis_results)} results to {csv_path}")
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            if write_header:
                writer.writeheader()
            for result in analysis_results:
                row = asdict(result)
                writer.writerow(row)
        print(f"Script analysis results appended to {csv_path}")
    except Exception as e:
        print(f"[SCRIPT CSV] Exception while appending to {csv_path}: {e}")

if __name__ == '__main__':
    # Example usage:
    sample_analysis = [
        ScriptAnalysis(
            video_filename="example_video.mp4",
            overall_message="How to build confidence through daily habits",
            script_purpose="Educational content to inspire personal growth",
            tonality="Motivational and encouraging",
            emotional_arc="Starts relatable, builds excitement, ends with empowerment",
            hook_effectiveness="Strong - uses personal story to create immediate connection",
            narrative_flow="Logical progression from problem to solution to action",
            transition_quality="Smooth transitions using bridging phrases",
            call_to_action="Clear and specific - try one habit for 7 days",
            recurring_patterns="Personal anecdotes, rhetorical questions, rule of three",
            line_by_line_analysis="Line 1: Hook with vulnerability. Line 2: Builds relatability...",
            effectiveness_score="8",
            improvement_suggestions="Could strengthen the middle section with more specific examples"
        )
    ]
    
    write_script_analysis_to_csv(sample_analysis, "script_analysis_results.csv")

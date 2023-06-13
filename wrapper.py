"""
Wrapper for MP4Box.
"""

__author__ = "aa.blinov"


import logging
import os
import subprocess
import traceback

from contextlib import contextmanager
from math import ceil
from typing import Callable, Generator, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@contextmanager
def cd(new_directory: str) -> Generator[None, None, None]:
    """
    An analogue of the cd command, implemented as a context manager.

    :param new_directory: New directory.
    """
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(new_directory))
    try:
        yield
    finally:
        os.chdir(prevdir)


class MP4BoxWrapper:
    """Class wrapper for MP4Box utility."""

    def __init__(
        self,
        original_video_path: str = "",
        video_segments: str = "",
        output_path: str = "",
        output_directory: str = ""
    ) -> None:
        """
        Initialize MP4BoxWrapper.


        :param original_video_path: Original video path.
        :param video_segments: Directory path containing MP4 videos.
        :param output_path: Output path with filename.
        :param output_directory: Output directory.
        """
        self.original_video_path = original_video_path
        self.video_segments = video_segments
        self.output_path = output_path
        self.output_directory = output_directory

    def _get_video_files(self) -> List[str]:
        """
        Get a list of MP4 video files in the specified directory.

        :return: List of MP4 video file paths.
        """
        video_files = []
        for file in os.listdir(self.video_segments):
            if file.endswith(".mp4"):
                video_files.append(os.path.join(self.video_segments, file))

        return video_files

    def _calculate_segment_count(self, video_path: str, duration: int) -> int:
        """
        Calculate the number of segments for a video
        based on the specified duration.

        :param video_path: Path to the video file.
        :paramduration: Duration (in seconds) for each video segment.
        :return: Number of segments for the video.
        """
        video_duration = self._get_video_duration(video_path)
        if video_duration < duration:
            return 0

        return ceil(video_duration / duration)

    def _get_video_duration(self, video_path: str) -> float:
        """
        Get the duration of a video.

        :param video_path: Path to the video file.
        :return: Duration of the video in seconds.
        """
        command = [
            "MP4Box",
            "-info",
            video_path
        ]
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT
        ).decode("utf-8")

        duration_line = next(
            (
                line
                for line in output.splitlines()
                if "Duration" in line
            ),
            None
        )
        if duration_line:
            duration_str = duration_line.split()[1].strip().replace(".", ":")
            hours, minutes, seconds, millisecond = map(
                int,
                duration_str.split(":")
            )

            return hours * 3600 + minutes * 60 + seconds + millisecond * 1e-3

        return 0

    def split_videos(self, duration: int) -> bool:
        """
        Split the original video into equal duration segments.

        :param duration: Duration (in seconds) for each video segment.
        :param original_video_path: Path to the original video file.
        :return: True if the split process was successful, False otherwise.
        """
        segment_count = self._calculate_segment_count(
            self.original_video_path,
            duration
        )

        if segment_count == 0:
            logger.info(
                f"Skipping file {self.original_video_path}: "
                "duration is less than the specified segment duration."
                )
            return False

        output_base = os.path.splitext(
            os.path.basename(self.original_video_path)
        )[0]
        for index in range(segment_count):
            start_time = index * duration
            output_path = os.path.join(
                self.output_directory,
                f"{output_base}_segment_{index+1}.mp4"
            )
            command = [
                "MP4Box",
                "-splitx", f"{start_time}:{start_time + duration}",
                self.original_video_path,
                "-out", output_path
            ]

            try:
                subprocess.run(command, check=True)
                logger.info(
                    f"Segment {index+1} of video "
                    f"{self.original_video_path} saved to {output_path}"
                )
            except subprocess.CalledProcessError:
                logger.error(
                    f"Error while splitting video {self.original_video_path}: "
                    f"{traceback.format_exc()}"
                )

                return False

        return True

    def merge_videos(self, sort_function: Callable) -> bool:
        """
        Merge MP4 videos in the specified directory into a single file.

        :return: True if the merge process was successful, False otherwise.
        """
        video_files = self._get_video_files()

        if not video_files:
            logger.info("No video files found in the directory.")
            return False

        if len(video_files) == 1:
            logger.info("Can't merge just one videoю")

        video_files.sort(key=sort_function)

        logger.info(f"Video files: {video_files}")
        videos_with_commands = []
        for video in video_files:
            if video == video_files[0]:
                videos_with_commands.append("-add")
                videos_with_commands.append(video)
                continue

            videos_with_commands.append("-cat")
            videos_with_commands.append(video)

        command = [
            "MP4Box",
            "-force-cat",
            *videos_with_commands,
            self.output_path
        ]
        try:
            subprocess.run(command, check=True)

            logger.info(
                "Videos merged successfully."
                f"Find result here: {self.output_path}"
            )
            return True
        except subprocess.CalledProcessError:
            logger.error(
                f"Error while merging videos: {traceback.format_exc()}"
            )
            return False


if __name__ == "__main__":
    mp4box = MP4BoxWrapper(
        original_video_path="original.mp4",
        video_segments="video_segments",
        output_path="merged.mp4",
        output_directory="video_segments"
    )
    # mp4box.split_videos(duration=60)

    mp4box.merge_videos(
        sort_function=lambda name: int(
            name.split("_")[-1].removesuffix(".mp4")
        )
    )

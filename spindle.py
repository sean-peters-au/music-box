"""
File: rod_with_handle.py
Generates a rod with a threaded section, a tapered tip, and a handle with wings.
"""

import cadquery as cq
import math
from cq_warehouse.thread import Thread

class Spindle:
    """
    Builds a rod with:
      - A bottom taper
      - A threaded portion using cq_warehouse
      - A circular handle
      - Four rectangular wings

    Public Methods:
        __init__(): Initializes the Spindle object and builds the geometry.
        export(filename: str): Exports the rod as an STL file.
        simulate(): Simulates rod usage (placeholder).
    """

    def __init__(self):
        # Taper dimensions
        self.taper_height = 2.0
        self.taper_diam_top = 5.0
        self.taper_diam_bot = 4.0

        # Threaded portion
        self.thread_height = 5.0
        self.thread_major_diam = 5.5
        self.thread_pitch = 0.625

        # Handle
        self.handle_diam   = 8.0
        self.handle_height = 4.0

        # Wings
        self.wing_count      = 4
        self.wing_height     = self.handle_height
        self.wing_radial_len = 4.0
        self.wing_width      = 4.0

        # Calculate z positions
        self.z_taper_start  = 0.0
        self.z_taper_end    = self.z_taper_start + self.taper_height
        self.z_thread_start = self.z_taper_end
        self.z_thread_end   = self.z_thread_start + self.thread_height
        self.z_handle_start = self.z_thread_end
        self.z_handle_end   = self.z_handle_start + self.handle_height

        # Build final rod geometry
        self._assembly = self._build_rod()

    def export(self, filename: str):
        """
        Exports the rod as an STL file with the specified filename.
        
        Args:
            filename (str): Output STL filename.
        """
        self._assembly.val().exportStl(filename, tolerance=0.01)
        print(f"Exported '{filename}'")

    def _build_rod(self) -> cq.Workplane:
        taper = self._make_taper()
        threaded_portion = self._make_threaded_portion()
        handle_circle = self._make_handle_circle()
        wings = self._make_wings()
        return taper.union(threaded_portion).union(handle_circle).union(wings)

    def _make_taper(self) -> cq.Workplane:
        return (
            cq.Workplane("XY")
            .circle(self.taper_diam_bot * 0.5)
            .workplane(offset=self.taper_height)
            .circle(self.taper_diam_top * 0.5)
            .loft(combine=True)
        )

    def _make_threaded_portion(self) -> cq.Workplane:
        # Create external thread surface
        my_thread = Thread(
            apex_radius=self.thread_major_diam / 2,
            apex_width=0.4,
            root_radius=4.5 / 2,  # approximate for an M5 root
            root_width=0.4,
            pitch=self.thread_pitch,
            length=self.thread_height,
            hand="right",
            end_finishes=("fade", "fade")
        )
        thread_cq = my_thread.cq_object.translate((0, 0, self.z_thread_start))

        # Create the minor-diameter rod core
        minor_diam = 4.2  # approximate for M5
        rod_core = (
            cq.Workplane("XY")
            .workplane(offset=self.z_thread_start)
            .circle(minor_diam * 0.5)
            .extrude(self.thread_height)
        )

        return rod_core.union(thread_cq)

    def _make_handle_circle(self) -> cq.Workplane:
        return (
            cq.Workplane("XY")
            .workplane(offset=self.z_handle_start)
            .circle(self.handle_diam * 0.5)
            .extrude(self.handle_height)
        )

    def _make_wings(self) -> cq.Workplane:
        wings_3d = cq.Workplane("XY")

        for i in range(self.wing_count):
            angle_deg = i * (360.0 / self.wing_count)
            single_wing_2d = cq.Workplane("XY").rect(self.wing_radial_len, self.wing_width, centered=True)
            single_wing_3d = single_wing_2d.extrude(self.wing_height)
            single_wing_3d = single_wing_3d.translate((self.handle_diam / 2, 0.0, self.z_handle_start))
            single_wing_3d = single_wing_3d.rotate((0, 0, 0), (0, 0, 1), angle_deg)
            wings_3d = wings_3d.union(single_wing_3d)

        return wings_3d
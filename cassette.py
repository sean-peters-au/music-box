"""
File: cassette.py
Generates a 3D cassette wheel for a music box.
"""

import cadquery as cq
import math

class Cassette:
    """
    Builds a music box cassette wheel using CadQuery.
    
    Public Methods:
        __init__(): Initializes the Cassette object and builds the geometry.
        export(filename: str): Exports the cassette as an STL file.
        simulate(): Simulates the music box by playing the cassette (placeholder).
    """

    def __init__(self):
        # Core cassette dimensions
        self.cassette_diameter = 13.0
        self.cassette_radius = self.cassette_diameter / 2.0
        self.cassette_total_height = 17.5
        self.cassette_wall_thickness = 4.0

        # Tine and pin dimensions
        self.total_tines = 18
        self.total_tine_width = 16.0
        self.tine_width = self.total_tine_width / self.total_tines
        self.num_pins = self.total_tines
        self.pin_radial_bump = 0.5
        self.pin_width = self.tine_width / 2
        self.pin_height = self.tine_width / 2
        self.pin_vertical_offset = 1.0

        # Base ring dimensions
        self.base_ring_height = 1.8
        self.base_ring_od = 15.0
        self.base_ring_id = 5.0

        # Top assembly dimensions
        self.lower_circle_height = 0.5
        self.lower_circle_diam = 16.0
        self.big_cog_height = 1.8
        self.small_cog_height = 1.5
        self.top_circle_height = 0.7
        
        self.big_cog_base_diam = 17.0
        self.big_cog_teeth_diam = 20.0
        self.num_teeth_big = 46
        
        self.small_cog_base_diam = 5.0
        self.small_cog_teeth_diam = 8.0
        self.num_teeth_small = 12
        
        self.top_circle_diam = 2.0

        # Musical information
        self.tine_notes = [
            "C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5",
            "E5", "F5", "G5", "A5", "B5", "C6", "D6", "E6", "F6"
        ]
        self.cassette_rotation_seconds = 20.0

        # Build final cassette geometry
        self._assembly = self._build_cassette()

    def export(self, filename: str):
        """
        Exports the cassette as an STL file with the specified filename.
        
        Args:
            filename (str): Output STL filename.
        """
        self._assembly.val().exportStl(filename, tolerance=0.01)
        print(f"Exported '{filename}'")

    def simulate(self):
        """
        Simulates the music box by playing the cassette (placeholder).
        """
        print("Simulating cassette... (audio simulation not implemented)")

    def _build_cassette(self) -> cq.Workplane:
        base_ring = self._make_base_ring()
        cassette_body = self._make_cassette_body()
        pins = self._make_pins()
        wheel_with_pins_and_base = cassette_body.union(pins).union(base_ring)
        top_assembly = self._make_top_assembly()
        return wheel_with_pins_and_base.union(top_assembly)

    def _make_base_ring(self) -> cq.Workplane:
        return (
            cq.Workplane("XY")
            .circle(self.base_ring_od / 2.0)
            .extrude(self.base_ring_height)
            .cut(
                cq.Workplane("XY")
                .circle(self.base_ring_id / 2.0)
                .extrude(self.base_ring_height)
            )
        )

    def _make_cassette_body(self) -> cq.Workplane:
        outer_cylinder = (
            cq.Workplane("XY")
            .workplane(offset=self.base_ring_height)
            .circle(self.cassette_radius)
            .extrude(self.cassette_total_height)
        )
        inner_cylinder = (
            cq.Workplane("XY")
            .workplane(offset=self.base_ring_height)
            .circle(self.cassette_radius - self.cassette_wall_thickness)
            .extrude(self.cassette_total_height)
        )
        return outer_cylinder.cut(inner_cylinder)

    def _make_pins(self) -> cq.Workplane:
        pins = cq.Workplane("XY")
        z_min = self.base_ring_height + self.pin_vertical_offset

        for i in range(self.num_pins):
            angle_deg = i * (360.0 / self.num_pins)
            angle_rad = math.radians(angle_deg)
            centre_offset = self.pin_width / 2
            spacing_offset = self.tine_width * i
            z_pin_center = z_min + spacing_offset + centre_offset
            x_center = self.cassette_radius * math.cos(angle_rad)
            y_center = self.cassette_radius * math.sin(angle_rad)
            z_bottom = z_pin_center - (self.pin_height / 2.0)

            single_pin = (
                cq.Workplane("XY")
                .box(
                    length=self.pin_radial_bump,
                    width=self.pin_width,
                    height=self.pin_height,
                    centered=(False, True, False)
                )
                .rotate((0, 0, 0), (0, 0, 1), angle_deg)
                .translate((x_center, y_center, z_bottom))
            )
            pins = pins.union(single_pin)
        return pins

    def _make_top_assembly(self) -> cq.Workplane:
        lower_circle_z_start = self.base_ring_height + self.cassette_total_height
        big_cog_z_start = lower_circle_z_start + self.lower_circle_height
        big_cog_z_top = big_cog_z_start + self.big_cog_height
        small_cog_z_start = big_cog_z_top
        small_cog_z_top = small_cog_z_start + self.small_cog_height
        top_circle_z_start = small_cog_z_top

        lower_circle = (
            cq.Workplane("XY")
            .workplane(offset=lower_circle_z_start)
            .circle(self.lower_circle_diam / 2.0)
            .extrude(self.lower_circle_height)
        )

        big_cog = self._make_big_cog(big_cog_z_start)
        small_cog = self._make_small_cog(small_cog_z_start)
        
        top_circle = (
            cq.Workplane("XY")
            .workplane(offset=top_circle_z_start)
            .circle(self.top_circle_diam / 2.0)
            .extrude(self.top_circle_height)
        )

        return lower_circle.union(big_cog).union(small_cog).union(top_circle)

    def _make_big_cog(self, z_start: float) -> cq.Workplane:
        big_cog_base_radius = self.big_cog_base_diam / 2.0
        big_cog_teeth_radius = self.big_cog_teeth_diam / 2.0
        big_cog_radial_thick = big_cog_teeth_radius - big_cog_base_radius

        big_cog_base = (
            cq.Workplane("XY")
            .workplane(offset=z_start)
            .circle(big_cog_base_radius)
            .extrude(self.big_cog_height)
        )

        big_cog_teeth = cq.Workplane("XY")
        for i in range(self.num_teeth_big):
            angle_deg = i * (360.0 / self.num_teeth_big)
            angle_rad = math.radians(angle_deg)
            tooth_3d = self._make_big_cog_tooth(
                radial_thickness=big_cog_radial_thick,
                base_width=1.0,
                tip_width=0.4,
                tooth_height=self.big_cog_height,
                fillet_3d=0.1
            )
            tooth_3d = (
                tooth_3d
                .rotate((0, 0, 0), (0, 0, 1), angle_deg)
                .translate((
                    big_cog_base_radius * math.cos(angle_rad),
                    big_cog_base_radius * math.sin(angle_rad),
                    z_start
                ))
            )
            big_cog_teeth = big_cog_teeth.union(tooth_3d)

        return big_cog_base.union(big_cog_teeth)

    def _make_small_cog(self, z_start: float) -> cq.Workplane:
        small_cog_base_radius = self.small_cog_base_diam / 2.0
        small_cog_teeth_radius = self.small_cog_teeth_diam / 2.0
        small_cog_radial_thick = small_cog_teeth_radius - small_cog_base_radius

        small_cog_base = (
            cq.Workplane("XY")
            .workplane(offset=z_start)
            .circle(small_cog_base_radius)
            .extrude(self.small_cog_height)
        )

        small_cog_teeth = cq.Workplane("XY")
        for i in range(self.num_teeth_small):
            angle_deg = i * (360.0 / self.num_teeth_small)
            angle_rad = math.radians(angle_deg)
            tooth_3d = self._make_small_cog_tooth(
                radial_thickness=small_cog_radial_thick,
                tooth_width=1.0,
                tooth_height=self.small_cog_height,
                fillet_3d=0.4
            )
            tooth_3d = (
                tooth_3d
                .rotate((0, 0, 0), (0, 0, 1), angle_deg)
                .translate((
                    small_cog_base_radius * math.cos(angle_rad),
                    small_cog_base_radius * math.sin(angle_rad),
                    z_start
                ))
            )
            small_cog_teeth = small_cog_teeth.union(tooth_3d)

        return small_cog_base.union(small_cog_teeth)

    def _make_big_cog_tooth(
        self,
        radial_thickness: float,
        base_width: float,
        tip_width: float,
        tooth_height: float,
        fillet_3d: float
    ) -> cq.Workplane:
        """
        Creates a trapezoidal tooth shape in 2D, extrudes it, then fillets
        the vertical edges. The trapezoid coordinates are defined by base_width,
        tip_width, and radial_thickness.
        """
        shape_2d = (
            cq.Workplane("XY")
            .polyline([
                (0, -base_width / 2.0),
                (0,  base_width / 2.0),
                (radial_thickness,  tip_width / 2.0),
                (radial_thickness, -tip_width / 2.0)
            ])
            .close()
        )
        tooth_3d = shape_2d.extrude(tooth_height)
        return tooth_3d.edges("|Z").fillet(fillet_3d)

    def _make_small_cog_tooth(
        self,
        radial_thickness: float,
        tooth_width: float,
        tooth_height: float,
        fillet_3d: float
    ) -> cq.Workplane:
        """
        Creates a rectangular tooth in 2D, extrudes it, then fillets all edges.
        """
        shape_2d = cq.Workplane("XY").rect(radial_thickness, tooth_width, centered=(False, True))
        tooth_3d = shape_2d.extrude(tooth_height)
        return tooth_3d.edges().fillet(fillet_3d)
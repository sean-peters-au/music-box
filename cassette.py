"""
File: cassette.py
Generates a 3D cassette wheel for a music box, using pin placement
based on incoming note/timing data.
"""

import math
import cadquery as cq
import cq_gears
from tine import Tine


class CassetteCAD:
    """
    Builds a music box cassette wheel using CadQuery, placing pins based on
    note/timing data. This class no longer extracts notes or plays them;
    pass in an existing list of (time_in_sec, note_name).

    Public Methods:
        __init__(note_events, rotation_duration=20.0): Initialize geometry data and build the cassette.
        export(filename: str): Exports the cassette as an STL file.
        get_assembly(): Access the underlying CadQuery assembly (for advanced usage).
    """

    def __init__(self, note_events, rotation_duration=20.0):
        """
        Args:
            note_events: A list of (time_in_sec, note_name) tuples.
            rotation_duration: How long (seconds) the cassette rotation takes.
        """
        # Pin/tine geometry
        self.tine_notes = Tine().notes
        self.total_tines = len(self.tine_notes)
        self.total_tine_width = 16.0
        self.tine_width = self.total_tine_width / self.total_tines
        self.pin_radial_bump = 0.5
        self.pin_width = self.tine_width / 2
        self.pin_height = self.tine_width / 2
        self.pin_vertical_offset = 1.5
        self.arc_safety_factor = 1.2

        # Base ring
        self.base_ring_height = 1.6
        self.base_ring_od = 15.0
        self.base_ring_id = 5.0

        # Cassette
        self.cassette_rotation_seconds = float(rotation_duration)
        self.cassette_diameter = 13.8
        self.cassette_radius = self.cassette_diameter / 2.0
        self.cassette_total_height = 17.5
        self.cassette_wall_thickness = 4.0
        
        # Interior taper parameters
        self.interior_opening_diameter = 6.0  # Opening diameter
        self.interior_center_diameter = 3.0   # Diameter at center
        self.taper_height = 3.0              # Height over which taper occurs
        self.interior_radius_opening = self.interior_opening_diameter / 2.0
        self.interior_radius = self.interior_center_diameter / 2.0

        self.min_note_angle_spacing = math.degrees(
            (self.pin_width * self.arc_safety_factor) / self.cassette_radius
        )

        # Top assembly
        # Lower circle, big cog, small cog, and a top circle

        # Lower circle
        self.lower_circle_height = 1.6
        self.lower_circle_diam = 16.0

        # Big cog
        self.big_cog_height = 1.6
        self.big_cog_base_diam = 16.8
        self.big_cog_teeth_diam = 19.5
        self.big_cog_num_teeth = 46

        # Small cog
        self.small_cog_height = 2.0
        self.small_cog_base_diam = 5.5
        self.small_cog_teeth_diam = 9.0
        self.small_cog_num_teeth = 12
        self.small_cog_base_radius = self.small_cog_base_diam / 2.0
        self.small_cog_teeth_radius = self.small_cog_teeth_diam / 2.0
        self.small_cog_radial_thick = self.small_cog_teeth_radius - self.small_cog_base_radius
        self.small_cog_teeth_width = 1.0

        # Top circle
        self.top_circle_height = 1.2
        self.top_circle_diam = 2.8

        # Store the incoming note events
        self.note_events = note_events

        # Build the geometry
        self._pins = self._generate_pins_from_notes()
        self._assembly = self._build_cassette()

    def export(self, filename: str):
        """
        Exports the cassette as an STL file with the specified filename.
        """
        self._assembly.val().exportStl(filename, tolerance=0.01)
        print(f"Exported '{filename}'")

    def get_assembly(self):
        """
        Returns the raw CadQuery Workplane assembly for advanced usage.
        """
        return self._assembly

    def _generate_pins_from_notes(self) -> cq.Workplane:
        """
        Create a set of pins based on note events, skipping overlapping pins
        for the same note if they occur too close in angle.
        """
        if not self.note_events:
            print("Warning: No notes detected to generate pins from.")
            return cq.Workplane("XY").box(0.0001, 0.0001, 0.0001)

        pins = cq.Workplane("XY")
        z_min = self.base_ring_height + self.pin_vertical_offset
        centre_offset = self.pin_width / 2.0

        last_note_angle = {}  # note_name -> angle_in_degrees

        for time_sec, note_name in self.note_events:
            if note_name not in self.tine_notes:
                # Skip unknown note
                continue

            angle_deg = (time_sec / self.cassette_rotation_seconds) * 360.0

            if note_name in last_note_angle:
                prev_angle = last_note_angle[note_name]
                if abs(angle_deg - prev_angle) < self.min_note_angle_spacing:
                    # Too close in angle for the same note, skip
                    continue

            note_index = self.tine_notes.index(note_name)
            spacing_offset = self.tine_width * note_index
            z_pin_center = z_min + spacing_offset + centre_offset
            z_bottom = z_pin_center - (self.pin_height / 2.0)

            x_center = self.cassette_radius * math.cos(math.radians(angle_deg))
            y_center = self.cassette_radius * math.sin(math.radians(angle_deg))

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
            last_note_angle[note_name] = angle_deg

        return pins

    def _build_cassette(self) -> cq.Workplane:
        base_ring = self._make_base_ring()
        cassette_body = self._make_cassette_body()
        wheel_with_pins_and_base = cassette_body.union(self._pins).union(base_ring)
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

        inner_cut = (
            cq.Workplane("XY")
            .workplane(offset=self.base_ring_height)
            .circle(self.interior_radius_opening)
            .workplane(offset=self.taper_height)
            .circle(self.interior_radius)
            .loft()
            .faces(">Z")
            .workplane()
            .circle(self.interior_radius)
            .extrude(self.cassette_total_height - self.taper_height)
        )

        return outer_cylinder.cut(inner_cut)

    def _make_top_assembly(self) -> cq.Workplane:
        # Add the flush offset to our calculations since we offset the small cog
        flush_offset = 0.5

        lower_circle_z_start = self.base_ring_height + self.cassette_total_height
        big_cog_z_start = lower_circle_z_start + self.lower_circle_height
        big_cog_z_top = big_cog_z_start + self.big_cog_height
        small_cog_z_start = big_cog_z_top
        small_cog_z_top = small_cog_z_start + self.small_cog_height - flush_offset  # Account for the offset
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
        for i in range(self.big_cog_num_teeth):
            angle_deg = i * (360.0 / self.big_cog_num_teeth)
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

    def _make_big_cog_tooth(
        self,
        radial_thickness: float,
        base_width: float,
        tip_width: float,
        tooth_height: float,
        fillet_3d: float
    ) -> cq.Workplane:
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

    def _make_small_cog(self, z_start: float) -> cq.Workplane:
        # These offsets are tweaks to get our bevel gear right
        flush_offset = 0.5  # z offset to make the cog sit flush with the big cog
        tooth_offset = 1  # outer radius offset to make the teeth longer

        z_start = z_start - flush_offset

        module = (self.small_cog_teeth_diam + tooth_offset) / (self.small_cog_num_teeth + 2)

        # Create the bevel gear
        gear = cq_gears.BevelGear(
            module=module,
            teeth_number=self.small_cog_num_teeth,
            width=self.small_cog_height,
            pressure_angle=20.0,
            spiral_angle=0.0,
            cone_angle=45.0,
            face_width = (self.small_cog_height + flush_offset)/ math.sin(math.radians(45.0))
        )

        # This is the raw 3D gear solid - wrap it in a Workplane
        small_cog_solid = cq.Workplane("XY").add(gear.build())

        # Create a cutting cylinder to remove top half of bevels
        cutting_cylinder = (
            cq.Workplane("XY")
            .circle(self.small_cog_teeth_diam)  # Make it bigger than the gear
            .extrude(self.small_cog_height)     # Cut at the base height
        )
        
        # Cut away everything above the base height
        small_cog_solid = small_cog_solid.intersect(cutting_cylinder)

        # Create a central ring
        central_ring = (
            cq.Workplane("XY")
            .circle(self.small_cog_base_radius)
            .extrude(self.small_cog_height)
        )

        # Combine the gear and ring
        small_cog_solid = small_cog_solid.union(central_ring)

        # Translate the gear so its bottom sits at z_start
        small_cog_solid = small_cog_solid.translate((0, 0, z_start))

        # Return as a CadQuery Workplane for consistency
        return small_cog_solid

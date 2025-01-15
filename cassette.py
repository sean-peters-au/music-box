import cadquery as cq
import math

"""
Creates a music box cassette wheel with:
- Base ring with 5mm center hole
- Main cylinder with spiral pins for the music comb
- Top assembly with large and small cogs for the winding mechanism
"""

# Main cassette dimensions
cassette_diameter = 13.0
cassette_radius = cassette_diameter / 2.0
cassette_total_height = 17.5
cassette_wall_thickness = 4.0

# Tine dimensions
total_tines = 18
total_tine_width = 16.0
tine_width = total_tine_width / total_tines

# Pin dimensions
num_pins = total_tines
pin_radial_bump = 0.5
pin_width = tine_width / 2
pin_height = tine_width / 2
pin_vertical_offset = 1.0

# Base ring dimensions
base_ring_height = 1.8
base_ring_od = 15.0
base_ring_id = 5.0

# Build base ring
base_ring = (
    cq.Workplane("XY")
    .circle(base_ring_od / 2.0)
    .extrude(base_ring_height)
    .cut(
        cq.Workplane("XY")
        .circle(base_ring_id / 2.0)
        .extrude(base_ring_height)
    )
)

# Build main cassette body
outer_cylinder = (
    cq.Workplane("XY")
    .workplane(offset=base_ring_height)
    .circle(cassette_radius)
    .extrude(cassette_total_height)
)

inner_cylinder = (
    cq.Workplane("XY")
    .workplane(offset=base_ring_height)
    .circle(cassette_radius - cassette_wall_thickness)
    .extrude(cassette_total_height)
)

cassette_body = outer_cylinder.cut(inner_cylinder)

# Create spiral pins
pins = cq.Workplane("XY")
z_min = base_ring_height + pin_vertical_offset

for i in range(num_pins):
    angle_deg = i * (360.0 / num_pins)
    angle_rad = math.radians(angle_deg)

    centre_offset = pin_width / 2
    spacing_offset = tine_width * i
    z_pin_center = z_min + spacing_offset + centre_offset

    x_center = cassette_radius * math.cos(angle_rad)
    y_center = cassette_radius * math.sin(angle_rad)

    z_bottom = z_pin_center - (pin_height / 2.0)

    single_pin = (
        cq.Workplane("XY")
        .box(
            length=pin_radial_bump,
            width=pin_width,
            height=pin_height,
            centered=(False, True, False)
        )
        .rotate((0, 0, 0), (0, 0, 1), angle_deg)
        .translate((x_center, y_center, z_bottom))
    )
    pins = pins.union(single_pin)

wheel_with_pins_and_base = cassette_body.union(pins).union(base_ring)

# Top assembly dimensions
big_cog_height = 1.8
small_cog_height = 1.5
top_circle_height = 0.7

# Calculate z-positions for stacked components
big_cog_z_start = base_ring_height + cassette_total_height
big_cog_z_top = big_cog_z_start + big_cog_height
small_cog_z_start = big_cog_z_top
small_cog_z_top = small_cog_z_start + small_cog_height
top_circle_z_start = small_cog_z_top
top_circle_z_top = top_circle_z_start + top_circle_height

# Large cog dimensions
big_cog_base_diam = 17.0
big_cog_teeth_diam = 20.0
num_teeth_big = 46
big_cog_base_radius = big_cog_base_diam / 2.0
big_cog_teeth_radius = big_cog_teeth_diam / 2.0
big_cog_radial_thick = big_cog_teeth_radius - big_cog_base_radius

# Small cog dimensions
small_cog_base_diam = 5.0
small_cog_teeth_diam = 8.0
num_teeth_small = 12
small_cog_base_radius = small_cog_base_diam / 2.0
small_cog_teeth_radius = small_cog_teeth_diam / 2.0
small_cog_radial_thick = small_cog_teeth_radius - small_cog_base_radius

top_circle_diam = 2.0

# Helper functions to create 3D-tooth solids
def make_big_cog_tooth(radial_thickness, base_width, tip_width, tooth_height, fillet_3d=0.1):
    """
    Makes a trapezoidal "triangular" tooth in 2D, extrudes it, then fillets
    the vertical edges. Coordinates for the trapezoid:
        (0, -base_width/2) → (0, base_width/2)
        → (radial_thickness, tip_width/2) → (radial_thickness, -tip_width/2)
    """
    shape_2d = (
        cq.Workplane("XY")
        .polyline([
            (0, -base_width/2.0),
            (0,  base_width/2.0),
            (radial_thickness,  tip_width/2.0),
            (radial_thickness, -tip_width/2.0)
        ])
        .close()
    )
    tooth_3d = shape_2d.extrude(tooth_height)
    tooth_3d = tooth_3d.edges("|Z").fillet(fillet_3d)
    return tooth_3d

def make_small_cog_tooth(radial_thickness, tooth_width, tooth_height, fillet_3d=0.4):
    """
    Makes a rectangular tooth in 2D, extrudes it, then fillets all edges heavily.
    """
    shape_2d = (
        cq.Workplane("XY")
        .rect(radial_thickness, tooth_width, centered=(False, True))
    )
    tooth_3d = shape_2d.extrude(tooth_height)
    tooth_3d = tooth_3d.edges().fillet(fillet_3d)
    return tooth_3d

# Base cylinders for each cog
big_cog_base = (
    cq.Workplane("XY")
    .workplane(offset=big_cog_z_start)
    .circle(big_cog_base_radius)
    .extrude(big_cog_height)
)

small_cog_base = (
    cq.Workplane("XY")
    .workplane(offset=small_cog_z_start)
    .circle(small_cog_base_radius)
    .extrude(small_cog_height)
)

# Teeth for the large cog (triangular, small fillets)
big_cog_teeth = cq.Workplane("XY")

for i in range(num_teeth_big):
    angle_deg = i * (360.0 / num_teeth_big)
    angle_rad = math.radians(angle_deg)

    tooth_3d = make_big_cog_tooth(
        radial_thickness = big_cog_radial_thick,
        base_width       = 1.0,
        tip_width        = 0.4,
        tooth_height     = big_cog_height,
        fillet_3d        = 0.1
    )

    tooth_3d = (
        tooth_3d
        .rotate((0,0,0), (0,0,1), angle_deg)
        .translate((
            big_cog_base_radius * math.cos(angle_rad),
            big_cog_base_radius * math.sin(angle_rad),
            big_cog_z_start
        ))
    )
    big_cog_teeth = big_cog_teeth.union(tooth_3d)

big_cog = big_cog_base.union(big_cog_teeth)

# Teeth for the small cog (rectangular, large 3D fillets)
small_cog_teeth = cq.Workplane("XY")

for i in range(num_teeth_small):
    angle_deg = i * (360.0 / num_teeth_small)
    angle_rad = math.radians(angle_deg)

    tooth_3d = make_small_cog_tooth(
        radial_thickness = small_cog_radial_thick,  # ~1.5
        tooth_width      = 1.0,
        tooth_height     = small_cog_height,        # 1.5
        fillet_3d        = 0.4
    )

    tooth_3d = (
        tooth_3d
        .rotate((0,0,0), (0,0,1), angle_deg)
        .translate((
            small_cog_base_radius * math.cos(angle_rad),
            small_cog_base_radius * math.sin(angle_rad),
            small_cog_z_start
        ))
    )
    small_cog_teeth = small_cog_teeth.union(tooth_3d)

small_cog = small_cog_base.union(small_cog_teeth)

# Small top circle
top_circle = (
    cq.Workplane("XY")
    .workplane(offset=top_circle_z_start)
    .circle(top_circle_diam / 2.0)
    .extrude(top_circle_height)
)

# Combine entire assembly: cassette + ring + pins + large cog + small cog + top circle
full_assembly = (
    wheel_with_pins_and_base
    .union(big_cog)
    .union(small_cog)
    .union(top_circle)
)

# Export
full_assembly.val().exportStl("cassette.stl", tolerance=0.01)
print("Exported 'cassette.stl'.")
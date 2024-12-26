import cadquery as cq
import math

# ----------------------
# PARAMETRIC DIMENSIONS
# ----------------------

cassette_diameter = 13.0
cassette_radius   = cassette_diameter / 2.0
cassette_total_height   = 20.0   # cylinder runs from Z=0 to Z=20
cassette_wall_thickness    = 4.0

# Pins
num_pins        = 16
pin_radial_bump = 0.5    # how far the pin extends radially beyond the cylinder OD
pin_width       = 0.5    # tangential width
pin_height      = 1.0    # vertical dimension

# --------------------------------------
# 1) CREATE THE OUTER CYLINDER (Z=0→20)
# --------------------------------------
# By default, extrude() from a workplane at Z=0 goes up to Z=20, so the bottom is at Z=0.

outer_cylinder = (
    cq.Workplane("XY")  
    .circle(cassette_radius)            # radius = 6.5 mm
    .extrude(cassette_total_height)           # from Z=0 up to Z=20
)

# ---------------------------------------------
# 2) CREATE THE STEPPED INTERIOR AS 1 EXTRUDE
# ---------------------------------------------
# We build one inner cylinder and subtract from the outer cylinder.

inner_cylinder = (
    cq.Workplane("XY")
    .workplane()
    .circle(cassette_radius - cassette_wall_thickness)      # 2.5 mm
    .extrude(cassette_total_height)                    # extrude 16 mm, Z=2..18
)

# Subtract the interior from the outer cylinder
cassette = outer_cylinder.cut(inner_cylinder)

# ---------------------------------------------
# 3) ADD PINS IN A SPIRAL FROM Z=4..16
# ---------------------------------------------
#
# We place 16 pins around the cylinder, each at a different angle (0..360) 
# and a different height (4..16).  The cylinder bottom is at Z=0, 
# so these pins are all in the central region.

pins = cq.Workplane("XY")

z_min = 4.0
z_max = 16.0
z_span = z_max - z_min  # 12 mm

for i in range(num_pins):
    angle_deg = i * (360.0 / num_pins)
    angle_rad = math.radians(angle_deg)
    
    # Spiral in Z
    z_pin_center = z_min + (z_span * i / (num_pins - 1))  # from 4..16
    
    # Cylinder surface in X/Y
    x_center = cassette_radius * math.cos(angle_rad)
    y_center = cassette_radius * math.sin(angle_rad)
    
    # We'll define a pin as a small "box" extending radially outward from the cylinder’s surface.
    z_bottom = z_pin_center - (pin_height / 2.0)
    
    single_pin = (
        cq.Workplane("XY")
        .box(
            length=pin_radial_bump,  # 0.5 mm radial extension
            width=pin_width,         # 0.5 mm wide tangentially
            height=pin_height,       # 1.0 mm tall
            centered=(False, True, False)
        )
        # Rotate that box around Z by angle_deg
        .rotate((0, 0, 0), (0, 0, 1), angle_deg)
        # Translate so the "cylinder-facing" face is at (cassette_radius, 0, z_bottom)
        .translate((x_center, y_center, z_bottom))
    )
    pins = pins.union(single_pin)

wheel_with_pins = cassette.union(pins)

# -----------------------------------------------------
# PART 2: EXTENDED COG ASSEMBLY ON TOP
# -----------------------------------------------------

# Heights
big_cog_height    = 1.8  # mm
small_cog_height  = 1.5  # mm
top_circle_height = 0.7  # mm
cog_extension_total_height = big_cog_height + small_cog_height + top_circle_height  # ~4 mm

# 1) LARGE COG (46 teeth) ------------------------------------------------
big_cog_base_diam    = 17.0  # mm (radius = 8.5 mm)
big_cog_teeth_diam   = 20.0  # mm (radius = 10 mm)
num_teeth_big        = 46
big_cog_z_start      = cassette_total_height        # e.g. 20
big_cog_z_top        = big_cog_z_start + big_cog_height  # 21.8

big_cog_base_radius  = big_cog_base_diam / 2.0   # 8.5
big_cog_teeth_radius = big_cog_teeth_diam / 2.0 # 10
big_cog_radial_thick = big_cog_teeth_radius - big_cog_base_radius  # 1.5 mm

# 2) SMALL COG (12 teeth) -----------------------------------------------
small_cog_base_diam   = 5.0   # mm (radius = 2.5 mm)
small_cog_teeth_diam  = 8.0   # mm (radius = 4 mm)
num_teeth_small       = 12
small_cog_z_start     = big_cog_z_top      # e.g. 21.8
small_cog_z_top       = small_cog_z_start + small_cog_height  # 23.3

small_cog_base_radius  = small_cog_base_diam / 2.0   # 2.5
small_cog_teeth_radius = small_cog_teeth_diam / 2.0  # 4.0
small_cog_radial_thick = small_cog_teeth_radius - small_cog_base_radius  # ~1.5 mm

# 3) SMALL TOP CIRCLE ---------------------------------------------------
top_circle_diam   = 2.0  # mm (radius = 1 mm)
top_circle_radius = top_circle_diam / 2.0
top_circle_z_start = small_cog_z_top  # e.g. 23.3
top_circle_z_top   = top_circle_z_start + top_circle_height  # 24.0

# -----------------------------------------------------
# HELPER FUNCTIONS FOR TOOTH SHAPES
# -----------------------------------------------------

def make_big_cog_tooth(
    radial_thickness,    # e.g. 1.5 mm
    base_width,          # e.g. 1.0 mm (at x=0)
    tip_width,           # e.g. 0.4 mm (at x= radial_thickness)
    tooth_height,        # e.g. 1.8 mm
    fillet_3d=0.1        # how big to round the edges in 3D
):
    """
    Creates a trapezoidal "triangular" tooth. We do a 2D polygon (a trapezoid),
    extrude it, then apply a 3D edge fillet.
    """
    # 1) Build a 2D trapezoid in the XY plane. Coordinates:
    #    (0, -base_width/2) -> (0, base_width/2)
    #    -> (radial_thickness, tip_width/2) -> (radial_thickness, -tip_width/2)
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

    # 2) Extrude this 2D shape into a 3D solid (height = tooth_height along Z)
    tooth_3d = shape_2d.extrude(tooth_height)

    # 3) Apply a 3D fillet on the edges
    #    - If you only want to round the vertical edges (parallel to Z):
    #        tooth_3d = tooth_3d.edges("|Z").fillet(fillet_3d)
    #    - If you want to round all edges (top/bottom too):
    #        tooth_3d = tooth_3d.edges().fillet(fillet_3d)
    #
    # For a triangular tooth, you might prefer just the vertical edges:
    tooth_3d = tooth_3d.edges("|Z").fillet(fillet_3d)

    return tooth_3d

def make_small_cog_tooth(
    radial_thickness,  # e.g. 1.5 mm
    tooth_width,       # e.g. 1.0 mm
    tooth_height,      # e.g. 1.5 mm
    fillet_3d=0.4
):
    """
    Creates a rectangular tooth with a big 3D fillet on all edges.
    """
    # 1) 2D rectangle
    shape_2d = (
        cq.Workplane("XY")
        .rect(radial_thickness, tooth_width, centered=(False, True))
        # 'rect' = width in X, height in Y here. 
        # Because we pass (False, True), it's not centered in X, but is in Y.
    )

    # 2) Extrude into 3D
    tooth_3d = shape_2d.extrude(tooth_height)

    # 3) Fillet the 3D edges
    tooth_3d = tooth_3d.edges().fillet(fillet_3d)

    return tooth_3d

# -----------------------------------------------------
# BUILD THE BASE CYLINDERS FOR EACH COG
# -----------------------------------------------------

big_cog_base = (
    cq.Workplane("XY")
    .workplane(offset=big_cog_z_start)  # e.g. offset=20
    .circle(big_cog_base_radius)        # 8.5 mm
    .extrude(big_cog_height)           # 1.8 mm tall
)

small_cog_base = (
    cq.Workplane("XY")
    .workplane(offset=small_cog_z_start)   # e.g. offset=21.8
    .circle(small_cog_base_radius)         # 2.5 mm
    .extrude(small_cog_height)            # 1.5 mm tall
)

# -----------------------------------------------------
# BUILD TEETH FOR LARGE COG (TRIANGULAR + small fillets)
# -----------------------------------------------------
big_cog_teeth = cq.Workplane("XY")

for i in range(num_teeth_big):
    angle_deg = i * (360.0 / num_teeth_big)
    angle_rad = math.radians(angle_deg)
    
    # We'll make a trapezoidal tooth shape (base_width=1.0, tip_width=0.4, etc.)
    # Adjust these if you need different geometry
    base_width = 1.0  # at x=0
    tip_width  = 0.4  # at x=1.5
    tooth_3d = make_big_cog_tooth(
        radial_thickness = big_cog_radial_thick,  # 1.5
        base_width       = base_width,
        tip_width        = tip_width,
        tooth_height     = big_cog_height,        # 1.8
        fillet_3d        = 0.1
    )
    
    # Rotate around Z and translate so it sits on the cylinder at radius=8.5
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

# -----------------------------------------------------
# BUILD TEETH FOR SMALL COG (RECT + very rounded edges)
# -----------------------------------------------------
small_cog_teeth = cq.Workplane("XY")

for i in range(num_teeth_small):
    angle_deg = i * (360.0 / num_teeth_small)
    angle_rad = math.radians(angle_deg)

    # We'll do a simple box extrude, then large 3D fillet on all edges
    tooth_3d = make_small_cog_tooth(
        radial_thickness = small_cog_radial_thick,  # ~1.5
        tooth_width      = 1.0,                     # tangential width
        tooth_height     = small_cog_height,        # 1.5
        fillet_3d        = 0.4                      # bigger rounding
    )
    
    # Rotate and translate so the inner face is at radius=2.5
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

# -----------------------------------------------------
# BUILD THE SMALL TOP CIRCLE
# -----------------------------------------------------
top_circle = (
    cq.Workplane("XY")
    .workplane(offset=top_circle_z_start)
    .circle(top_circle_radius)      # 1 mm
    .extrude(top_circle_height)     # 0.7 mm
)

# -----------------------------------------------------
# COMBINE ALL INTO A SINGLE SOLID
# -----------------------------------------------------
full_assembly = wheel_with_pins.union(big_cog).union(small_cog).union(top_circle)

# ---------------------------------
# EXPORT STL
# ---------------------------------
full_assembly.val().exportStl("music_box_wheel_with_cog_teeth.stl", tolerance=0.01)
print("Exported 'music_box_wheel_with_cog_teeth.stl'.")
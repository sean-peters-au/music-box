import cadquery as cq
import math

# -----------------------------------------------------------------
# IMPORTANT: From cq_warehouse.thread import Thread, ThreadType, etc.
# -----------------------------------------------------------------
from cq_warehouse.thread import Thread

# -----------------------------
# PARAMETERS
# -----------------------------
# Bottom Taper
taper_height = 2.0        # mm
taper_diam_top = 5.0      # mm  # meets the thread portion
taper_diam_bot = 4.0      # mm  # tip at the very bottom

# Threaded Portion
thread_height = 5.0       # mm
thread_major_diam = 5.5   # mm (outer thread diameter)
# Adjust pitch for 8 revolutions over 5mm
thread_pitch = 0.625      # was 0.8

# The handle "blocker circle"
handle_diam   = 8.0       # mm
handle_height = 4.0       # mm

# Four rectangular wings
wing_count       = 4
wing_height      = handle_height  # 4 mm
wing_radial_len  = 4.0            # how far out from the handle's perimeter
wing_width       = 4.0            # the "circumferential" dimension

# -----------------------------
# Z-Positions
# -----------------------------
z_taper_start  = 0.0
z_taper_end    = z_taper_start + taper_height       # ~2
z_thread_start = z_taper_end                        # ~2
z_thread_end   = z_thread_start + thread_height     # ~7
z_handle_start = z_thread_end                       # ~7
z_handle_end   = z_handle_start + handle_height     # ~11

# -----------------------------
# 1) MAKE THE BOTTOM TAPER
#    Loft from 4 mm Ø at z=0 to 5 mm Ø at z=2
# -----------------------------
taper_solid = (
    cq.Workplane("XY")
    .circle(taper_diam_bot * 0.5)         # radius=2.0
    .workplane(offset=taper_height)       # up 2 mm
    .circle(taper_diam_top * 0.5)         # radius=2.5
    .loft(combine=True)
)

# -----------------------------
# 2) CREATE THE THREADED SECTION
#    Using cq_warehouse Thread to generate true external threads
# -----------------------------
#
# The library's Thread object needs:
#  - length (thread_height)
#  - major_diameter (outer diameter of the thread)
#  - pitch (for M5 typically ~0.8)
#  - thread_type (like ThreadType.ISO)
#  - a workplane axis or a cylinder to revolve around
#
# We'll place the thread so it starts at z=2 and ends at z=7.

# The thread library can generate a "Thread" object that we can position
# by translating. We'll define it along the Z-axis, from 0..thread_height,
# then translate it up to z=2.

my_thread = Thread(
    # For M5 thread:
    apex_radius=thread_major_diam/2,  # outer radius = 2.5mm
    apex_width=0.4,                   # reduced from 0.65 for finer threads
    root_radius=4.5/2,               # increased slightly for shallower threads
    root_width=0.4,                  # reduced to match apex_width
    pitch=thread_pitch,              # 0.625mm for 8 revolutions
    length=thread_height,            # 5mm
    hand="right",
    end_finishes=("fade", "fade")
)
thread_cq = my_thread.cq_object

# By default, this thread might start at z=0..5. We'll translate it so the bottom is at z_thread_start=2.
# Also note: The library forms threads *around the origin* if not otherwise specified.
# We'll keep the center axis on Z. If the rod's major diameter = 5 mm => radius=2.5,
# the thread is around x=0,y=0. That should align with the taper top if we just shift up in Z.

thread_solid = thread_cq.translate((0, 0, z_thread_start))

# NOTE: The "Thread" shape from cq_warehouse is usually the threaded *outer surface*.
# If you want a *solid* rod with threads, you can union it with a cylinder of the minor diameter inside.
# For M5, minor diameter is ~4.2 mm (depending on standard). We'll do that:

minor_diam = 4.2  # approximate for M5
rod_core = (
    cq.Workplane("XY")
    .workplane(offset=z_thread_start)
    .circle(minor_diam*0.5)
    .extrude(thread_height)
)
threaded_portion = rod_core.union(thread_solid)

# -----------------------------
# 3) HANDLE “BLOCKER CIRCLE” at z=7..11
#    8 mm Ø => radius=4
# -----------------------------
handle_circle = (
    cq.Workplane("XY")
    .workplane(offset=z_handle_start)
    .circle(handle_diam*0.5)  # 4 mm radius
    .extrude(handle_height)   # 4 mm tall
)

# -----------------------------
# 4) FOUR RECTANGULAR WINGS
#    Each: 4×4 mm cross-section, protruding radially outward
#    from the handle's perimeter (radius=4 mm).
# -----------------------------
wing_solid = cq.Workplane("XY")

for i in range(wing_count):
    angle_deg = i*(360.0/wing_count)  # 0,90,180,270
    
    # Create wing centered at origin
    single_wing_2d = (
        cq.Workplane("XY")
        .rect(wing_radial_len, wing_width, centered=True)
    )
    single_wing_3d = single_wing_2d.extrude(wing_height)

    # First translate outward by handle radius
    single_wing_3d = single_wing_3d.translate((handle_diam/2, 0.0, z_handle_start))
    # Then rotate to position
    single_wing_3d = single_wing_3d.rotate((0,0,0), (0,0,1), angle_deg)

    wing_solid = wing_solid.union(single_wing_3d)

# -----------------------------
# COMBINE EVERYTHING
# -----------------------------
part = (
    taper_solid
    .union(threaded_portion)
    .union(handle_circle)
    .union(wing_solid)
)

# -----------------------------
# EXPORT STL
# -----------------------------
part.val().exportStl("rod_with_handle.stl", tolerance=0.01)
print("Exported 'rod_with_handle.stl'.")

# Music Box

This is a simple project to modify a mechnical music box with custom songs. 

This seemed like a fun idea to test out my new 3D printer, and to put a smile on my 4 month old son's face. It worked! Although - probably more efficient to just pull funny faces at him :)

## Instructions

- Buy this music box https://www.aliexpress.com/item/1005006822293186.html

- Setup your environment
```sh
conda create -n music_box python=3.10
conda activate music_box
conda install -c conda-forge cadquery trimesh
pip install git+https://github.com/gumyr/cq_warehouse.git#egg=cq-warehouse
```

- Print cassette from your mp3
```sh
python musicbox.py mp3/twinkle-twinkle-little-star.mp3
```

- Print the components in `stl/`

- Remove the existing spindle (I managed to just reverse it out with an appropriately sized drill bit).
<image>

- Remove the existing cassette
<image>

- Place in new cassette
<image>

- Thread in the new spindle.
<image>
# Music Box

This is a simple project to modify a mechnical music box with custom songs. 

## Instructions

- Buy this music box https://www.aliexpress.com/item/1005006822293186.html

- Setup your environment
```sh
brew install aubio
conda create -n music_box python=3.10
conda activate music_box
conda install -c conda-forge cadquery trimesh anthropic
pip install click
pip install git+https://github.com/gumyr/cq_warehouse.git#egg=cq-warehouse
pip install git+https://github.com/meadiode/cq_gears.git
export ANTHROPIC_API_KEY=your_key_here
```

- Print cassette of a song you'd like
```sh
python main.py --input-test "fur elise"
```

- Print the components in `stl/`

- Remove the existing spindle

- Remove the existing cassette, and replace with your printed cassette

- Thread in the new spindle.
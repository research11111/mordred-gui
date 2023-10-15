# Mordred-gui
Compute properties on molecules.
![Alt text](./doc/media/main.png)

### Install
#### From source
```bash
conda create -n mordredgui python=3.11 && \
    conda activate mordredgui && \
    pip install git+https://github.com/research11111/mordred-gui.git#egg=mordred-gui
```
#### From github
Download a release from [releases](https://github.com/research11111/mordred-gui/releases), then
```bash
conda create -n mordredgui python=3.11 && \
    conda activate mordredgui && \
    pip install mordred_gui-*.whl
```
### Run
```bash
mordred-gui
```
For example Polycaprolactone SMILES:  
```
CCC(COC(=O)CCCCCO)(COC(=O)CCCCCO)COC(=O)CCCCCO
```
### Developp
#### Install
```bash
conda create -n mordredgui python=3.11 && \
    conda activate mordredgui && \
    pip install poetry && \
    poetry install --no-root && \
    pip install -e .
```
#### Build
```bash
poetry build
```

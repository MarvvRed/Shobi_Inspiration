from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'fragrantica-scraper-archive'/'social-cards'/'images'
ids=[3,4,9,17,433,714,845,905]
thumbs=[]
for fid in ids:
    files=list(D.glob(f'*_{fid}.jpeg'))
    if not files: continue
    im=Image.open(files[0]).convert('RGB').resize((300,300))
    draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,120,24),fill='white')
    draw.text((5,5),f'ID {fid}',fill='black')
    thumbs.append(im)
canvas=Image.new('RGB',(600,300*((len(thumbs)+1)//2)),'white')
for i,im in enumerate(thumbs):
    canvas.paste(im,((i%2)*300,(i//2)*300))
canvas.save(ROOT/'social-card-layout-calibration.jpg',quality=92)
print('saved',len(thumbs))

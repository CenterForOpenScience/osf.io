from PIL import Image
import math
import os

#This script enlarges institions shield imamges so the corners show when they are displayed as circles.

INSTITUTIONS_IMG_PATH =  '../website/static/img/institutions/'

def pythagonreanTheorem(x,y):
    return math.ceil((x**2 + y**2)**.5)

def resize(img):
    newSize = int(pythagonreanTheorem(img.size[0],img.size[1])) # new corners within circle
    newImg = Image.new('RGBA', (newSize,newSize), 'white')
    newImg.paste(img, (newSize/2-img.size[0]/2,newSize/2-img.size[1]/2)) #center in larger img
    return newImg

def alphaToWhite(img):
    pixeldata = list(img.getdata())
    for i,pixel in enumerate(pixeldata):
        if len(pixel) == 4:
            if pixel[3] != 255:
                pixeldata[i] = (255,255,255,255)

    img.putdata(pixeldata)
    return img


def generateTestHTML(size):

    path = INSTITUTIONS_IMG_PATH + 'shields-rounded-corners/'
    f = open('image_maniplation/test_rounded_corners.html','w')
    f.write('<body style=background-color:lightgrey;>\n')
    for shieldName in os.listdir(path):
        f.write('<img src={0} style="border-radius:100%;height:{1};width:{1};">\n'.format('../'+path + shieldName, size))
    f.write('</body>')
    f.close()

def main():
    path = INSTITUTIONS_IMG_PATH + 'shields/'

    for shield in os.listdir(path):
        if shield[:-4] + '-rounded-corners.png' not in os.listdir(INSTITUTIONS_IMG_PATH + 'shields-rounded-corners/'): # shields shouldn't be over written
            img = Image.open(path + shield)
            img = resize(img)
            img = alphaToWhite(img)
            img.save(INSTITUTIONS_IMG_PATH + 'shields-rounded-corners/'+ shield[:-4] + '-rounded-corners.png')

    generateTestHTML(size=100)
    print("This script removes transparency from images, check the test html to ensure a the quality has been maintained")
main()
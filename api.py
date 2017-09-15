import urllib2
import json

html = urllib2.urlopen('http://api.douban.com/v2/book/isbn/9787218087351')
print (html)
# hjson = json.loads(heml.read())
#
# print hjson['rating']
# print hjson['images']['large']
# print hjson['summary']
import recommonmark.parser as parser
from recommonmark.parser import CommonMarkParser

__all__ = ['CommonMarkParser']

old_image = parser.image


def image(block):
    img_node = old_image(block)
    if '#' in img_node['uri']:
        img_node['uri'], params = img_node['uri'].rsplit('#', 1)
        for param in params.split(','):
            key, value = param.split('=', 1)
            img_node[key] = value

    return img_node

parser.image = image

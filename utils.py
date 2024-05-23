# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import numpy
import random
import addon_utils


def prefs():
    user_preferences = bpy.context.preferences
    return user_preferences.addons[__package__].preferences 


def gob_version():
    return str([addon.bl_info.get('version', (-1,-1,-1)) for addon in addon_utils.modules() if addon.bl_info['name'] == 'GoB'][0])
     
    
def max_list_value(list):
    """ retrun biggest value of a list"""
    i = numpy.argmax(list)
    v = list[i]
    return (i, v)


def avg_list_value(list):
    """ retrun average value of a list"""
    avgData=[]
    for obj in list:
        i = numpy.argmax(obj)
        avgData.append(obj[i])
    avg = numpy.average(avgData)
    return (avg)


def random_color(base=16):    
    randcolor = "%5x" % random.randint(0x1111, 0xFFFF)
    return int(randcolor, base)



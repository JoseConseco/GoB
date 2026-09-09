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
import time
import numpy
import random
import addon_utils
import platform


def prefs():
    user_preferences = bpy.context.preferences
    return user_preferences.addons[__package__].preferences 


def platform_path_storage_key(property_name, system=None):
    """Return the platform-specific storage key for a path preference."""
    system = system or platform.system()
    if system == "Darwin":
        return f"{property_name}_macos"
    if system == "Windows":
        return f"{property_name}_windows"
    return property_name


def legacy_path_matches_platform(path, system=None):
    """Reject a legacy path only when it clearly belongs to the other platform."""
    normalized_path = path.strip().replace("\\", "/")
    system = system or platform.system()
    is_windows_drive = (
        len(normalized_path) > 2
        and normalized_path[0].isalpha()
        and normalized_path[1:3] == ":/"
    )
    is_windows_unc = normalized_path.startswith("//")

    if system == "Darwin":
        return not (
            normalized_path.lower().endswith(".exe")
            or is_windows_drive
            or is_windows_unc
        )
    if system == "Windows":
        return not (
            (normalized_path.startswith("/") and not is_windows_unc)
            or normalized_path.lower().endswith(".app")
        )
    return True


def get_platform_path(property_name, preferences=None, system=None):
    preferences = preferences or prefs()
    storage_key = platform_path_storage_key(property_name, system)

    if storage_key == property_name or preferences.is_property_set(storage_key):
        return getattr(preferences, storage_key)

    legacy_path = getattr(preferences, property_name)
    if legacy_path and legacy_path_matches_platform(legacy_path, system):
        return legacy_path
    return getattr(preferences, storage_key)


def set_platform_path(property_name, value, preferences=None, system=None):
    preferences = preferences or prefs()
    setattr(preferences, platform_path_storage_key(property_name, system), value)


def migrate_legacy_platform_path(property_name, preferences, system=None):
    storage_key = platform_path_storage_key(property_name, system)
    if storage_key == property_name or preferences.is_property_set(storage_key):
        return

    legacy_path = getattr(preferences, property_name)
    if legacy_path and legacy_path_matches_platform(legacy_path, system):
        setattr(preferences, storage_key, legacy_path)


def get_zbrush_exec(preferences=None, system=None):
    return get_platform_path("zbrush_exec", preferences, system)


def set_zbrush_exec(value, preferences=None, system=None):
    set_platform_path("zbrush_exec", value, preferences, system)


def migrate_legacy_zbrush_exec(preferences, system=None):
    migrate_legacy_platform_path("zbrush_exec", preferences, system)


def get_project_path(preferences=None, system=None):
    return get_platform_path("project_path", preferences, system)


def migrate_legacy_project_path(preferences, system=None):
    migrate_legacy_platform_path("project_path", preferences, system)


def get_pixologic_path(preferences=None, system=None):
    return get_platform_path("pixologoc_path", preferences, system)


def migrate_legacy_pixologic_path(preferences, system=None):
    migrate_legacy_platform_path("pixologoc_path", preferences, system)


def gob_version():
    return str([addon.bl_info.get('version', (-1,-1,-1)) for addon in addon_utils.modules() if addon.bl_info.get('name','') == 'GoB'][0])
     
    
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



def profiler(start_time=False, string=None):    

    elapsed = time.perf_counter()
    measured_time = elapsed-start_time
    if start_time:
        print("{:.6f}(ms) <<".format(measured_time*1000), string)  
    else:
        print("debug_profiling: ", string)          
             
    start_time = time.perf_counter()
    return start_time

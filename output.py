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

def ShowReport(self, message = [], title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        for i in message:
            self.layout.label(text=i)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


def profiler(start_time=False, string=None):    

    elapsed = time.perf_counter()
    measured_time = elapsed-start_time
    if start_time:
        print("{:.6f}(ms) <<".format(measured_time*1000), string)  
    else:
        print("debug_profiling: ", string)          
             
    start_time = time.perf_counter()
    return start_time  
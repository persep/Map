"""Create all Israel Hiking and Biking maps

This is the main script used to build the maps.

The map creation is done in phases. The first phase creates the trails overlay map.
Each of the following phases updates the tiles required for an offline map 
and launches the appropriate MOBAC task.

Progress is tracked by creating "phase done" files. 
An incomplete map creation will be resumes at the first incomplete phase.
"""

import os
import os.path
from datetime import *
import string
import errno
from maperipy import *
from maperipy.osm import *
from GenIsraelHikingTiles import IsraelHikingTileGenCommand

# TODO Separate OSM update and its server definitions from the Israel Hiking code

start_time = datetime.now()

# http://stackoverflow.com/questions/749711/how-to-get-the-python-exe-location-programmatically
MaperitiveDir = os.path.dirname(os.path.dirname(os.path.normpath(os.__file__)))
# App.log('MaperitiveDir: '+MaperitiveDir)
ProgramFiles = os.path.normpath(os.path.dirname(MaperitiveDir))
# App.log('ProgramFiles: '+ProgramFiles)
ProjectDir = os.path.dirname(os.path.dirname(os.path.normpath(App.script_dir)))
# App.log('App.script_dir: '+App.script_dir)
# App.log('ProjectDir: '+ProjectDir)
App.run_command('change-dir dir="'+ProjectDir +'"')
os.chdir(ProjectDir)

def mkdir_p(path):
    if os.path.isdir(path):
        return
    os.makedirs(path)

def silent_remove(filename):
    # https://www.python.org/dev/peps/pep-3151/#lack-of-fine-grained-exceptions
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def silent_rename(filename, new_filename):
    silent_remove(new_filename)
    try:
        os.rename(filename, new_filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def safe_rename(filename, new_filename):
    silent_remove(new_filename+".old")
    silent_rename(new_filename, new_filename+".old")
    try:
        os.rename(filename, new_filename)
        silent_remove(new_filename+".old")
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def add_to_PATH(app_name):
    for path_dir in string.split(os.environ["PATH"], os.pathsep):
        for ext in string.split(os.pathsep+os.environ["PATHEXT"], os.pathsep):
            if os.path.exists(os.path.join(path_dir, app_name+ext)):
                # Application already found in PATH
                return
    full_app_name=os.path.join(ProgramFiles, app_name)
    if not os.path.isdir(full_app_name):
        # Application not a sibling of Maperitive
        App.log("Warning: "+app_name+" location not found. Could not add it to PATH.")
        return
    os.environ["PATH"] = string.join([os.environ["PATH"],full_app_name], os.pathsep)

add_to_PATH("wget")
add_to_PATH("Mobile Atlas Creator")

phases = [
    'OverlayTiles',
    'IsraelHiking15',
    'IsraelMTB15',
    'IsraelHiking16',
    'IsraelMTB16']
remainingPhases = []

def done_file(phase):
    return os.path.join(ProjectDir, 'Cache', phase+'.done')

def mark_done(phase):
    open(done_file(phase), 'a').close()
    App.log(phase+' phase is done.')
    gen_cmd.print_timer("Current duration:", (datetime.now()-start_time).total_seconds())

def MOBAC(map_script, map_description):
    program_line = os.path.join(ProgramFiles, "Mobile Atlas Creator", map_script)
    if os.path.exists(program_line):
        App.log("=== Launch creation of "+map_description+" ===")
        App.log('App.start_program("'+program_line+'", [])')
        App.start_program(program_line, [])

# Keep batch windows open up to 24 hours
os.environ["NOPAUSE"] = "TIMEOUT /T 86400"

gen_cmd =  IsraelHikingTileGenCommand()

# Create a new map if all phased were done
phases_done = 0
for phase in phases:
    if not os.path.exists(done_file(phase)):
        remainingPhases.append(phase)

if remainingPhases == []:
    for phase in phases:
        os.remove(done_file(phase))
"""
# TODO openstreetmap.fr's israel minutely updates
# The OSM data used by the latest tile generation
latest = os.path.join(ProjectDir, 'Cache', 'israel-latest.osm.pbf')
# URL for downloading the above
latest_url = "http://download.openstreetmap.fr/extracts/asia/israel-latest.osm.pbf"
# The changes since then
osm_change = os.path.join(ProjectDir, 'Cache', 'israel-update.osc')
# The updated OSM data for this tile generation
updated = os.path.join(ProjectDir, 'Cache', 'israel-updated.osm.pbf')
# Source of the OSM diff files
base_url = "download.openstreetmap.fr/replication/asia/israel"
change_resolution = "--minute"
"""

# Geofaprik's israel-and-palestine daily updates
# The OSM data used by the latest tile generation
latest = os.path.join(ProjectDir, 'Cache', 'israel-and-palestine-latest.osm.pbf')
# URL for downloading the above
latest_url = "http://download.geofabrik.de/asia/israel-and-palestine-latest.osm.pbf"
# The changes since then
osm_change = os.path.join(ProjectDir, 'Cache', 'israel-and-palestine-update.osc')
# The updated OSM data for this tile generation
updated = os.path.join(ProjectDir, 'Cache', 'israel-and-palestine-updated.osm.pbf')
# Source of the OSM diff files
base_url = "download.geofabrik.de/asia/israel-and-palestine-updates"
change_resolution = "--sporadic"

# Output directory for the tiles of all maps
site_dir = os.path.join(ProjectDir, 'Site')

App.run_command("use-ruleset location="+os.path.join("Rules", "empty.mrules"))
if os.path.exists(latest):
    if remainingPhases == phases or remainingPhases == []:
        App.log("=== Downloading map changes ===")
        exit_code = App.run_program("osmup.exe", 7200, [
            latest, osm_change, "--base-url="+base_url, change_resolution])
        gen_cmd.print_timer("Current duration:", (datetime.now()-start_time).total_seconds())
        if exit_code == 21:
            # osmupdate: Your OSM file is already up-to-date
            App.log("=== No changes found, map update completed ===")
            remainingPhases = []
        else:
            App.log("=== Creating updated map data ===")
            App.run_program("osmconvert.exe", 300, [latest, osm_change, "-o="+updated])
            remainingPhases = phases
            gen_cmd.print_timer("Current duration:", (datetime.now()-start_time).total_seconds())
    else:
        App.log('=== Continueing execution of the previous tile generation ===')  
        App.log('Remaining phases: '+', '.join(remainingPhases))
        App.run_command("pause 15000")

    if remainingPhases:
        # Osm Change analysis
        App.log("=== Analyzing map changes ===")
        gen_cmd.osmChangeRead(osm_change, latest, updated)
        (changed, guard) = gen_cmd.statistics()
        if not changed:
            remainingPhases = []
        gen_cmd.print_timer("Current duration:", (datetime.now()-start_time).total_seconds())
else:
    # Create base map if latest does not exist
    App.log("=== Non-Incremental Tile Generation ===")
    if os.path.exists(updated) and remainingPhases:
        App.log('=== Continueing execution of the previous tile generation ===')  
        App.log('Remaining phases: '+', '.join(remainingPhases))
        App.run_command("pause 15000")
    else:
        App.log("=== Downloading the latest map data ===")
        # wget for Windows: http://gnuwin32.sourceforge.net/packages/wget.htm
        App.run_program('wget.exe', 1200,
                        ["--timestamping",
                         "--no-directories", "--no-verbose",
                         '--directory-prefix="'+os.path.join(ProjectDir, 'Cache')+'"',
                         latest_url])
        safe_rename(latest, updated)
        remainingPhases = phases
    App.log("=== Loading the map ===")
    Map.add_osm_source(updated)
    gen_cmd.timestamp = datetime.fromtimestamp(os.path.getmtime(updated))
    gen_cmd.print_timer("Current duration:", (datetime.now()-start_time).total_seconds())

if remainingPhases:
    # Tile generation
    phase = 'OverlayTiles'
    if phase in remainingPhases:
        App.log("=== Create Trails Overlay tiles ===")
        App.run_command("set-setting name=map.coastline.mode value=ignore")
        App.run_command("use-ruleset location="+os.path.join("Rules", "IsraelHikingOverlay.mrules"))
        App.run_command("apply-ruleset")
        App.collect_garbage()
        gen_cmd.GenToDirectory(7, 16, os.path.join(site_dir, 'OverlayTiles'))
        MOBAC("All IsraelHikingOverlay Maps.bat", "Oruxmaps Israel Hiking Overlay Map")
        mark_done(phase)
    else:
        App.log(phase+' phase skipped.')

    if [val for val in ['IsraelHiking15', 'IsraelMTB15', 'IsraelHiking16', 'IsraelMTB16']
            if val in remainingPhases]:
        App.run_command("run-script file="+os.path.join("Scripts", "Maperitive", "IsraelDecoration.mscript"))

    phase = 'IsraelHiking15'
    if phase in remainingPhases:
        App.log('Updating the Israel Hiking Map')
        App.run_command("use-ruleset "+os.path.join("Rules", "IsraelHiking.mrules"))
        App.run_command("apply-ruleset")
        App.collect_garbage()
        App.log('=== creating tiles for Israel Hiking zoom levels up to 15 ===')  
        gen_cmd.GenToDirectory(7, 15, os.path.join(site_dir, 'Tiles'))
        MOBAC("Create Israel Hiking.bat", "Oruxmaps Israel Hiking map")
        mark_done(phase)
    else:
        App.log(phase+' phase skipped.')

    phase = 'IsraelMTB15'
    if phase in remainingPhases:
        App.log('Updating the Israel MTB Map')
        App.run_command("use-ruleset "+os.path.join("Rules", "mtbmap.mrules"))
        App.run_command("apply-ruleset")
        App.collect_garbage()
        App.log('=== creating tiles for Israel MTB zoom levels up to 15 ===')  
        gen_cmd.GenToDirectory(7, 15, os.path.join(site_dir, 'mtbTiles'))
        MOBAC("Create Israel MTB.bat", "Oruxmaps Israel MTB map")
        mark_done(phase)
    else:
        App.log(phase+' phase skipped.')

    phase = 'IsraelHiking16'
    if phase in remainingPhases:
        App.log('Updating the Israel Hiking Map')
        App.run_command("use-ruleset "+os.path.join("Rules", "IsraelHiking.mrules"))
        App.run_command("apply-ruleset")
        App.collect_garbage()
        App.log("=== Create tiles for Israel Hiking zoom level 16 ===")
        gen_cmd.GenToDirectory(16, 16, os.path.join(site_dir, 'Tiles'))
        MOBAC("Create Israel Hiking 16.bat", "Oruxmaps Israel Hiking detailed map")
        mark_done(phase)
    else:
        App.log(phase+' phase skipped.')

    phase = 'IsraelMTB16'
    if phase in remainingPhases:
        App.log('Updating the Israel MTB Map')
        App.run_command("use-ruleset "+os.path.join("Rules", "mtbmap.mrules"))
        App.run_command("apply-ruleset")
        App.collect_garbage()
        App.log('=== creating Israel MTB zoom level 16 ===')  
        gen_cmd.GenToDirectory(16, 16, os.path.join(site_dir, 'mtbTiles'))
        MOBAC("Create Israel MTB 16.bat", "Oruxmaps Israel MTB detailed map")
        mark_done(phase)
    else:
        App.log(phase+' phase skipped.')

    for phase in phases:
        try:
            os.remove(done_file(phase))
        except:
            pass

    # Don't loose the original latest pbf if something goes wrong
    safe_rename(updated, latest)
    Map.clear()

duration = datetime.now()-start_time
gen_cmd.print_timer("Total time:", duration.total_seconds())

Map.clear()  # DEBUG
App.collect_garbage()  # DEBUG

# vim: shiftwidth=4 expandtab

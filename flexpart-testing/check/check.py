#!/usr/bin/env python

"""
@author: morton

Don Morton
Boreal Scientific Computing LLC, Fairbanks, Alaska, USA
Don.Morton@borealscicomp.com
http://www.borealscicomp.com/


@contributors

Christian Maurer
ZAMG, Vienna, Austria
christian.maurer@zamg.ac.at
Delia Arnold
ZAMG, Vienna, Austria
delia.arnold-arias@zamg.ac.at

"""



#import tempfile
import argparse
import os
import uuid
import sys
import shutil

import distrotest.TestSuite as TS

import flextest.FlexpartCase as FlexpartCase
import flextest.FlexpartExecutable as Fexec
import flextest.FlexpartErrors as FlexpartErrors
import flextest.flexread.FlexpartOutput as FlexpartOutput
import flextest.OutputCompare as OutputCompare

# Set up for argument parsing

# This used for checking presence of any files listed in arguments
def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("File %s not found" % arg)
    else:
        return arg


cmdline_makefile_path = None   # Initial value for the makefile from command line

parser = argparse.ArgumentParser()

parser.add_argument("xml_file", help="Full path to XML spec file",
                    action="store")

parser.add_argument("-m", "--makefile",
                    help="Full path to makefile",
                    action="store", dest="cmdline_makefile_path")

parser.add_argument("-k", "--keeptemp",
                    help="Keep temporary directories",
                    action="store_true")

args = parser.parse_args()

#print 'args.xml_file: ', args.xml_file
#print 'args.cmdline_makefile_path: ', args.cmdline_makefile_path

# Get the command line arguments after parsing.  Some might be "None"
xml_file = args.xml_file
cmdline_makefile_path = args.cmdline_makefile_path

# By default, temp directories will be cleaned up unless test fails.  We can choose
# to keep these with the appropriate command-line flag -k or --keeptemp
if args.keeptemp:
    clean_up = False
    print 'Will retain temporary directories'
else:
    clean_up = True
    print 'Will delete temporary directories if test is successful'
#sys.exit()

# Bring in the XML filename from the command line

XML_FILE = [xml_file]



# This is where lots of temporary directories are going to be created.
# User needs to make sure it is OK to put them in here.  Note that there
# is currently no clean up of these directories if a test fails.  
# The logic is that users
# might want to go back and look at the test directories, so auto-cleanup
# prevents that.
SCRATCH_DIR = '/tmp'


t = TS.TestSuite(xml_files=XML_FILE)

distro_list = t.get_distribution_list()

the_distro = distro_list[0]

'''
print the_distro.get_descr()
print the_distro.get_distro_path()
print the_distro.get_makefile_path()
print the_distro.get_parmod_path()
'''

# Create a temporary directory for compiling the distribution
distro_destdir_name = SCRATCH_DIR + '/distrotest_' + str(uuid.uuid4()) 
print 'distro_destdir_name: ' + distro_destdir_name


good_init = False
compile_success = False
all_success = False
try:
    srcdir = os.path.realpath(the_distro.get_distro_path())
    
    # The makefile path will come from command line, if available, 
    if cmdline_makefile_path:
        makefile = cmdline_makefile_path
    else:
        print 'WARNING... makefile path not specified'

    print 'using makefile: ' + str(makefile)
    
    parmodfile = os.path.realpath(the_distro.get_parmod_path())
    exec_name = the_distro.get_exec_name()
    exec_obj = Fexec.FlexpartExecutable(srcdir=srcdir,
                                        destdir=distro_destdir_name,
                                        makefile=makefile,
                                        parmodfile=parmodfile,
                                        executable_name=exec_name)
    good_init = True
except Exception as e:
    print 'Bad instantiation: ' + str(e)
    pass

if good_init:
    print 'Executable exists: ' + str(exec_obj.executable_exists())



    # Try to compile it
    print; print '============================'; print
    print 'compile test...'
    print 'Compile directory: ' + distro_destdir_name
    compile_success = exec_obj.compile_it()
    
    print 'compile_success: ' + str(compile_success)
    print 'Executable exists: ' + str(exec_obj.executable_exists())    
    
    if compile_success:
        flexpart_executable = distro_destdir_name + '/' + exec_name        
    else:
        print
        print '*** COMPILE TEST FAILED ***'
        print
        print 'If Executable exists is True, it is probably finding an old executable'
        print 'The test distribution is located in: ' + distro_destdir_name
        print 'The makefile being used is: ' + makefile
        print 'You should try to go there and see if you can find error by compiling by hand'
    
    print; print '============================'; print

# Next, get the met cases for this distro list and iterate through them

if compile_success:

#   We add a logical variable that will indicate us whether any
#      of the tests failed and, if so, prevent the erasing of  
#      the temporal directories
    all_success = True   
    list_all_cases = []
    
    met_case_list = the_distro.get_met_case_list()
    print met_case_list
    for the_met_case in met_case_list:
        

        print; print '****************************'
        the_descr = the_met_case.get_descr()
        print 'Running MetCase: ' + the_descr
        the_metfile_dir = os.path.realpath(the_met_case.get_metfile_dir())
        print 'Met file dir: ' + the_metfile_dir
        try:
            the_metnestfile_dir = os.path.realpath(the_met_case.get_metnestfile_dir())
            print 'Met Nest file dir: ' + the_metnestfile_dir
        except:
            #print ' ... no nested met input used'
            the_metnestfile_dir = None

        print '****************************'; print
        
        # Iterate through each of the run cases in the met_case
        run_case_list = the_met_case.get_run_case_list()
        
        for the_run_case in run_case_list:
            the_descr = the_run_case.get_descr()
            print 'Running RunCase: ' + the_descr
            
            case_dir = os.path.realpath(the_run_case.get_case_dir())
            print 'Case dir: ' + case_dir
            case_rundir = SCRATCH_DIR + '/caserun_' + str(uuid.uuid4())             
            list_all_cases.append(case_rundir) # add the case_dir into a list for cleaning
            control_data_dir = os.path.realpath(the_run_case.get_control_data_dir())
            
            basic_test_list = the_run_case.get_test_list()
            run_success = False
            
            print; print '============================'
            print 'Case Test ' + str(the_descr) + '...'
            print 'Case template directory: ' + case_dir
            print 'Case run directory: ' + case_rundir
            print 'Control data directory: ' + control_data_dir
            print 'Met file dir: ' + the_metfile_dir
            if the_metnestfile_dir:
                print 'Met Nest file dir: ' + the_metnestfile_dir
            print 'Executable: ' + flexpart_executable
            print 'Number of basic tests: ' + str(len(basic_test_list))
            print '============================'; print
            
            
            # Create the case object
            case_obj = FlexpartCase.FlexpartCase(
                             src_dir=case_dir,
                             dest_dir=case_rundir,
                             met_dir=the_metfile_dir,
                             met_nest_dir=the_metnestfile_dir,
                             flexpart_exe=flexpart_executable
                                                 )
        
            # Run the case
            run_val = case_obj.run()
        
            # Test for success
            run_success = case_obj.success()
            print 'run_success: ' + str(run_success)
            print 'Execution time: %7.2E seconds' % \
                  (case_obj.execution_time_seconds()) 
            if not run_success:
                all_success = False # to know wheter any of the tests failed
                print 'run test failed'
                print 'The test distribution is located in: ' + case_rundir
                print 'The FLEXPART executable being used is: ' + flexpart_executable
                print 'You should try to go there and see if you can find error by running by hand'
                print 'There is a file named stdout.txt in there which might give a clue'
        
            print; print '============================'; print
                    
            
        
            if run_success:
            
            
                output_compare = OutputCompare.OutputCompare(output_dir=case_rundir + '/output',
                                                control_output_dir=control_data_dir)
                                                
                #print output_compare.query_test_types()


                for the_basic_test in basic_test_list:
                    
                    the_descr = the_basic_test.get_descr()
                    test_type = the_basic_test.get_test_type()
                    threshold = the_basic_test.get_threshold()
                    

                    print; print '-----------------------'
                    print 'Basic Test'
                    print 'Description: ' + the_descr
                    print 'Test type: ' + test_type
                    print 'Threshold: %7.1E' % (threshold)

                    
                    the_error = output_compare.calculate_test_minus_control(test_type=test_type)
                    
                    print 'Test performed.  Error = %7.1E' % (the_error)
                    if the_error > threshold:
                        all_success = False
                        print 'Test failed...'
                        print '    Test data is in: ' + case_rundir + '/output'
                        print '    Control data is in: ' + control_data_dir
                    else:
                        print 'Test passed'

                    print '-----------------------'; print

if clean_up:
    if all_success:
        print 'All tests passed, erasing temporary directories'
        print distro_destdir_name
        shutil.rmtree(distro_destdir_name)
        for item in list_all_cases:
            print item
            shutil.rmtree(item)
    else:
        print 'Some of the tests failed, temp dirs not erased'
        print ' WARNING: remember to remove directories manually'
        print '          when you have finished checking them'            
        
        
        
        
        
    
    
    




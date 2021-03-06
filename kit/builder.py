import os
import shutil
import storage
import scanner
import utility


# Copies headers in module to build/headers/name, dropping one 
# directory layer (i.e. name/sources/header.h => name/header.h)
# TODO: minimize headers
def prepare_headers(name):
	root = storage.module_path(name)
	baseheaders = root + '/build/headers/kit'
	headers = baseheaders + '/' + name
	for path in utility.headers_under(root):
		if path.find('build') == 0:
			continue
		dest = path.replace(root + '/', '')
		dest = '/'.join(dest.split('/')[1:])
		if not os.path.exists(headers):
			os.makedirs(headers)
		shutil.copy(path, headers + '/' + dest)

		if path.replace(root + '/sources/', '') == name + '.h':
			shutil.copy(path, baseheaders)
	print ' - prepared headers'



# Ensure that module is compiled.
def ready_indexed_module(name):
	if storage.module_compiled(name):
		print utility.color(' - already compiled', 'green')
	else:
		path = storage.module_path(name)
		build_directory(path)
		prepare_headers(name)
		print utility.color(' - compiled module: ' + name, 'green')


# Generates CMakeLists file for project. This should be removed after
# compilation.
def generate_cmake(path, deps):
	name = os.path.abspath(path).split('/')[-1]
	with open(path + '/CMakeLists.txt', 'w') as f:
		f.write('project(KitModule C)\n')
		f.write('cmake_minimum_required(VERSION 2.6)\n')
		f.write('cmake_policy(VERSION 2.6)\n')
		f.write('set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)\n')
		f.write('set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)\n')
		f.write('set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)\n')
		f.write('SET(CMAKE_C_FLAGS  "' + scanner.metadata()['cflags'] + '")\n')
		f.write('file(GLOB_RECURSE sources "sources/*.h" "sources/*.c")\n')
		f.write('file(GLOB_RECURSE test_sources "tests/*.h" "tests/*.c")\n')
		f.write('set(headers "")\n')
		for dep in deps:
			f.write('file(GLOB_RECURSE t1 "' + storage.module_header_path(dep) + '/*.h")\n')
			f.write('set(t2 ${headers})\n')
			f.write('set(headers ${t1} ${t2})\n')

		if os.path.exists(path + '/sources/main.c'):
			f.write('add_executable(' + name + ' ${sources} ${headers})\n')
			f.write('set(test_sources2 ${sources} ${test_sources})\n')
			f.write('list(REMOVE_ITEM test_sources2 "${PROJECT_SOURCE_DIR}/sources/main.c")\n')
			f.write('add_executable(tests ${test_sources2} ${headers})\n')
		else:
			f.write('add_library(' + name + ' STATIC ${sources} ${headers})\n')
			f.write('add_executable(tests ${sources} ${test_sources} ${headers})\n')
		for dep in deps:
			f.write('add_library(' + dep + ' SHARED IMPORTED)\n')
			f.write('set_target_properties(' + dep + ' PROPERTIES IMPORTED_LOCATION "' + storage.module_library_path(dep) + '")\n')
			f.write('TARGET_LINK_LIBRARIES(tests ' + dep + ')\n')
			f.write('TARGET_LINK_LIBRARIES(' + name + ' ' + dep + ')\n')
			f.write('include_directories(' + storage.module_header_path(dep) + ')\n')
	print ' - generated CMakeLists.txt'



# Compiles executables and libraries for given project, assuming
# that all dependencies have been resolved a priori.
def make(path):
	print ' - running `make`...'
	wd = os.getcwd()
	os.chdir(path)
	os.system('mkdir -p build')
	os.chdir('build')
	c1 = os.system('cmake -Wno-dev .. > /dev/null')
	c2 = os.system('make > /dev/null')
	os.system('rm ../CMakeLists.txt')
	os.chdir(wd)
	if c1 == 0 and c2 == 0:
		print utility.color(' - build successfull', 'green')
	else:
		print utility.color(' - build failed', 'red')
		exit(1)


	
# Compiles libraries and headers for given directory.
def build_directory(path):
	deps = scanner.directory_dependencies(path)
	for dep in deps:
		print ' - resolving dependency:', dep
		if not storage.contains_module(dep):
			if storage.remote_contains_module(dep):
				storage.fetch_module(dep)
			else:
				print utility.color(' - module not found: ' + dep, 'red')
				print utility.color(' - build failed', 'red')
				exit(1)
		ready_indexed_module(dep)
	generate_cmake(path, deps)
	make(path)

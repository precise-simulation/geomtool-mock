#include <core/register_archive.hpp>
#include <occ/occgeom.hpp>

namespace
{
void __cdecl register_windows_static_netgen_archive_types()
{
  static ngcore::RegisterClassForArchive<netgen::NetgenGeometry>
    netgen_geometry_registration;
  static ngcore::RegisterClassForArchive<netgen::OCCGeometry, netgen::NetgenGeometry>
    occ_geometry_registration;
}

#pragma section(".CRT$XCV", read)
extern "C" __declspec(allocate(".CRT$XCV"))
void (__cdecl* geomtool_windows_static_netgen_registration_initializer)() =
  register_windows_static_netgen_archive_types;

#pragma comment(linker, "/include:geomtool_windows_static_netgen_registration_initializer")
}

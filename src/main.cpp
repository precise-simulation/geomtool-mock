#include "globals.hpp"
#include "mock.hpp"

#include <Standard_Version.hxx>

#include <exception>
#include <iostream>
#include <string>
#include <vector>

namespace
{
std::vector<std::string> arguments(int argc, char** argv, int start)
{
  std::vector<std::string> result;
  for(int index = start; index < argc; ++index)
    result.emplace_back(argv[index]);
  return result;
}

int command_version()
{
  std::cout << "geomtool " << VERSION << "\n";
  std::cout << "OCCT " << OCC_VERSION_COMPLETE << "\n";
#ifdef MESH_NETGEN
  std::cout << "Netgen v" << GEOMTOOL_MOCK_NETGEN_VERSION << "\n";
#endif
#ifdef MESH_INSTANTMESH2D
  std::cout << "InstantMesh2D enabled\n";
#endif
  return 0;
}
} // namespace

int main(int argc, char** argv)
{
  try
  {
    if(argc < 2)
    {
      std::cerr << "usage: geomtool <ver|block|mesh> ...\n";
      return 2;
    }

    const std::string command(argv[1]);
    if(command == "ver")
      return command_version();
    if(command == "block")
      return mock_block(arguments(argc, argv, 2));
#ifdef MESH
    if(command == "mesh")
      return mock_mesh(arguments(argc, argv, 2));
#endif

    std::cerr << "unsupported command: " << command << "\n";
    return 2;
  }
  catch(const std::exception& error)
  {
    std::cerr << "geomtool mock error: " << error.what() << "\n";
    return 1;
  }
}

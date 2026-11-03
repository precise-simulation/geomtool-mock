#include "mock.hpp"

#include <iostream>

int mock_mesh(const std::vector<std::string>& args)
{
#ifdef MESH_NETGEN
  return mock_mesh_netgen(args);
#else
  (void)args;
  std::cerr << "mock InstantMesh2D profile does not implement the mesh command\n";
  return 2;
#endif
}

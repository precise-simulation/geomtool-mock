#pragma once

#include <string>
#include <vector>

int mock_block(const std::vector<std::string>& args);

#ifdef MESH
int mock_mesh(const std::vector<std::string>& args);
#endif

#ifdef MESH_NETGEN
int mock_mesh_netgen(const std::vector<std::string>& args);
#endif

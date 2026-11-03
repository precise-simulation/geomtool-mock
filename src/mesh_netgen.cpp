#include "mock.hpp"

namespace nglib
{
#include <nglib.h>
#include <nglib_occ.h>
}

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
using nglib::NG_OK;
using nglib::Ng_DeleteMesh;
using nglib::Ng_Exit;
using nglib::Ng_GenerateVolumeMesh;
using nglib::Ng_GetNE;
using nglib::Ng_GetNP;
using nglib::Ng_GetNSE;
using nglib::Ng_Init;
using nglib::Ng_Mesh;
using nglib::Ng_Meshing_Parameters;
using nglib::Ng_NewMesh;
using nglib::Ng_OCC_DeleteGeometry;
using nglib::Ng_OCC_GenerateEdgeMesh;
using nglib::Ng_OCC_GenerateSurfaceMesh;
using nglib::Ng_OCC_Geometry;
using nglib::Ng_OCC_Load_BREP;
using nglib::Ng_OCC_SetLocalMeshSize;
using nglib::Ng_SaveMesh;

[[noreturn]] void fail(const std::string& message)
{
  throw std::runtime_error(message);
}

double parse_double(const std::string& value, const std::string& name)
{
  std::size_t end = 0;
  const double parsed = std::stod(value, &end);
  if(end != value.size())
    fail("invalid " + name + ": " + value);
  return parsed;
}

std::string lower_extension(const std::filesystem::path& path)
{
  std::string extension = path.extension().string();
  std::transform(extension.begin(), extension.end(), extension.begin(),
                 [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  return extension;
}

class NetgenSession
{
public:
  NetgenSession() { Ng_Init(); }
  ~NetgenSession()
  {
    if(mesh_)
      Ng_DeleteMesh(mesh_);
    if(geometry_)
      Ng_OCC_DeleteGeometry(geometry_);
    Ng_Exit();
  }

  NetgenSession(const NetgenSession&) = delete;
  NetgenSession& operator=(const NetgenSession&) = delete;

  Ng_OCC_Geometry* geometry_ = nullptr;
  Ng_Mesh* mesh_ = nullptr;
};
} // namespace

int mock_mesh_netgen(const std::vector<std::string>& args)
{
  if(args.size() < 5)
    fail("usage: geomtool mesh input.brep -hmax size -o output.vol");

  const std::filesystem::path input(args[0]);
  if(lower_extension(input) != ".brep")
    fail("mock mesh supports BREP input only");

  double hmax = 0.0;
  std::filesystem::path output;
  for(std::size_t index = 1; index < args.size(); ++index)
  {
    const std::string& arg = args[index];
    if(arg == "-hmax")
    {
      if(index + 1 >= args.size())
        fail("-hmax requires a value");
      hmax = parse_double(args[++index], "hmax");
    }
    else if(arg == "-o")
    {
      if(index + 1 >= args.size())
        fail("-o requires an output path");
      output = args[++index];
    }
    else
    {
      fail("unsupported mesh argument: " + arg);
    }
  }

  if(hmax <= 0.0)
    fail("mesh requires positive -hmax");
  if(output.empty())
    fail("mesh requires -o output.vol");
  if(lower_extension(output) != ".vol")
    fail("mock mesh output must use .vol");

  NetgenSession session;
  session.geometry_ = Ng_OCC_Load_BREP(input.string().c_str());
  if(!session.geometry_)
    fail("Netgen failed to load BREP: " + input.string());

  session.mesh_ = Ng_NewMesh();
  if(!session.mesh_)
    fail("Netgen failed to allocate a mesh");

  Ng_Meshing_Parameters parameters;
  parameters.maxh = hmax;
  parameters.minh = 0.0;
  parameters.fineness = 0.5;

  if(Ng_OCC_SetLocalMeshSize(session.geometry_, session.mesh_, &parameters) != NG_OK)
    fail("Netgen local mesh sizing failed");
  if(Ng_OCC_GenerateEdgeMesh(session.geometry_, session.mesh_, &parameters) != NG_OK)
    fail("Netgen edge meshing failed");
  if(Ng_OCC_GenerateSurfaceMesh(session.geometry_, session.mesh_, &parameters) != NG_OK)
    fail("Netgen surface meshing failed");
  if(Ng_GenerateVolumeMesh(session.mesh_, &parameters) != NG_OK)
    fail("Netgen volume meshing failed");

  const int points = Ng_GetNP(session.mesh_);
  const int surface = Ng_GetNSE(session.mesh_);
  const int volume = Ng_GetNE(session.mesh_);
  if(points <= 0 || surface <= 0 || volume <= 0)
    fail("Netgen produced an incomplete mesh");

  Ng_SaveMesh(session.mesh_, output.string().c_str());
  if(!std::filesystem::is_regular_file(output) ||
     std::filesystem::file_size(output) == 0)
    fail("Netgen did not write a nonempty VOL mesh");

  std::cout << "mesh points=" << points
            << " surface=" << surface
            << " volume=" << volume << "\n";
  return 0;
}

#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepMesh_IncrementalMesh.hxx>
#include <BRepTools.hxx>
#include <StlAPI_Writer.hxx>
#include <Standard_Version.hxx>
#include <TopoDS_Shape.hxx>
#include <gp_Pnt.hxx>

namespace nglib
{
#include <nglib.h>
#include <nglib_occ.h>
}

#include <algorithm>
#include <cctype>
#include <exception>
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

[[noreturn]] void fail(const std::string &message)
{
  throw std::runtime_error(message);
}

double parse_double(const std::string &value, const std::string &name)
{
  std::size_t end = 0;
  const double parsed = std::stod(value, &end);
  if(end != value.size())
    fail("invalid " + name + ": " + value);
  return parsed;
}

std::string lower_extension(const std::filesystem::path &path)
{
  std::string extension = path.extension().string();
  std::transform(extension.begin(), extension.end(), extension.begin(),
                 [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  return extension;
}

std::vector<std::string> output_arguments(int argc, char **argv, int start)
{
  for(int i = start; i < argc; ++i)
  {
    if(std::string(argv[i]) == "-o")
    {
      if(i + 1 >= argc)
        fail("-o requires at least one output path");
      std::vector<std::string> outputs;
      for(++i; i < argc; ++i)
        outputs.emplace_back(argv[i]);
      return outputs;
    }
  }
  fail("missing -o output path");
}

int command_version()
{
  std::cout << "geomtool mock\n";
  std::cout << "OCCT " << OCC_VERSION_COMPLETE << "\n";
  std::cout << "Netgen v" << GEOMTOOL_MOCK_NETGEN_VERSION << "\n";
  return 0;
}

int command_block(int argc, char **argv)
{
  if(argc < 10)
    fail("usage: geomtool block xmin xmax ymin ymax zmin zmax -o output...");

  const double xmin = parse_double(argv[2], "xmin");
  const double xmax = parse_double(argv[3], "xmax");
  const double ymin = parse_double(argv[4], "ymin");
  const double ymax = parse_double(argv[5], "ymax");
  const double zmin = parse_double(argv[6], "zmin");
  const double zmax = parse_double(argv[7], "zmax");
  if(xmax <= xmin || ymax <= ymin || zmax <= zmin)
    fail("block bounds must have positive size");

  const TopoDS_Shape shape =
      BRepPrimAPI_MakeBox(gp_Pnt(xmin, ymin, zmin), gp_Pnt(xmax, ymax, zmax)).Shape();

  const auto outputs = output_arguments(argc, argv, 8);
  for(const std::string &name : outputs)
  {
    const std::filesystem::path path(name);
    const std::string extension = lower_extension(path);
    if(extension == ".brep")
    {
      if(!BRepTools::Write(shape, path.string().c_str()))
        fail("failed to write BREP: " + path.string());
    }
    else if(extension == ".stl")
    {
      BRepMesh_IncrementalMesh triangulation(shape, 0.05);
      triangulation.Perform();
      if(!triangulation.IsDone())
        fail("failed to triangulate shape for STL output");
      StlAPI_Writer writer;
      if(!writer.Write(shape, path.string().c_str()))
        fail("failed to write STL: " + path.string());
    }
    else
    {
      fail("unsupported block output format: " + extension);
    }
  }

  std::cout << "block outputs=" << outputs.size() << "\n";
  return 0;
}

class NetgenSession
{
public:
  NetgenSession()
  {
    Ng_Init();
  }

  ~NetgenSession()
  {
    if(mesh_)
      Ng_DeleteMesh(mesh_);
    if(geometry_)
      Ng_OCC_DeleteGeometry(geometry_);
    Ng_Exit();
  }

  NetgenSession(const NetgenSession &) = delete;
  NetgenSession &operator=(const NetgenSession &) = delete;

  Ng_OCC_Geometry *geometry_ = nullptr;
  Ng_Mesh *mesh_ = nullptr;
};

int command_mesh(int argc, char **argv)
{
  if(argc < 7)
    fail("usage: geomtool mesh input.brep -hmax size -o output.vol");

  const std::filesystem::path input(argv[2]);
  if(lower_extension(input) != ".brep")
    fail("mock mesh supports BREP input only");

  double hmax = 0.0;
  std::filesystem::path output;
  for(int i = 3; i < argc; ++i)
  {
    const std::string arg(argv[i]);
    if(arg == "-hmax")
    {
      if(i + 1 >= argc)
        fail("-hmax requires a value");
      hmax = parse_double(argv[++i], "hmax");
    }
    else if(arg == "-o")
    {
      if(i + 1 >= argc)
        fail("-o requires an output path");
      output = argv[++i];
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
  if(!std::filesystem::is_regular_file(output) || std::filesystem::file_size(output) == 0)
    fail("Netgen did not write a nonempty VOL mesh");

  std::cout << "mesh points=" << points
            << " surface=" << surface
            << " volume=" << volume << "\n";
  return 0;
}
} // namespace

int main(int argc, char **argv)
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
      return command_block(argc, argv);
    if(command == "mesh")
      return command_mesh(argc, argv);

    std::cerr << "unsupported command: " << command << "\n";
    return 2;
  }
  catch(const std::exception &error)
  {
    std::cerr << "geomtool mock error: " << error.what() << "\n";
    return 1;
  }
}

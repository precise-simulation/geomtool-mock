#include "mock.hpp"

#include <BRepMesh_IncrementalMesh.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepTools.hxx>
#include <StlAPI_Writer.hxx>
#include <TopoDS_Shape.hxx>
#include <gp_Pnt.hxx>

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
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
} // namespace

int mock_block(const std::vector<std::string>& args)
{
  if(args.size() < 9)
    fail("usage: geomtool block xmin xmax ymin ymax zmin zmax -o output...");

  const double xmin = parse_double(args[0], "xmin");
  const double xmax = parse_double(args[1], "xmax");
  const double ymin = parse_double(args[2], "ymin");
  const double ymax = parse_double(args[3], "ymax");
  const double zmin = parse_double(args[4], "zmin");
  const double zmax = parse_double(args[5], "zmax");
  if(xmax <= xmin || ymax <= ymin || zmax <= zmin)
    fail("block bounds must have positive size");
  if(args[6] != "-o")
    fail("block requires -o followed by one or more outputs");

  const TopoDS_Shape shape =
      BRepPrimAPI_MakeBox(gp_Pnt(xmin, ymin, zmin), gp_Pnt(xmax, ymax, zmax)).Shape();

  int outputs = 0;
  for(std::size_t index = 7; index < args.size(); ++index)
  {
    const std::filesystem::path path(args[index]);
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
    ++outputs;
  }

  if(outputs == 0)
    fail("block requires at least one output");
  std::cout << "block outputs=" << outputs << "\n";
  return 0;
}

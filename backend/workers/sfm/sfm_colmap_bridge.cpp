/**
 * VĀSTU Spatial Computing - Point 19: Structure-from-Motion COLMAP Bridge (C++17)
 *
 * High-performance C++ bridge for COLMAP-based sparse 3D reconstruction:
 * 1. Image feature database initialization and feature extraction.
 * 2. Exhaustive and sequential image pair matching with geometric verification.
 * 3. Incremental Structure-from-Motion (SfM) camera pose estimation.
 * 4. Sparse 3D point triangulation and bundle adjustment.
 * 5. Reconstruction quality statistics computation.
 * 6. Export to sparse_points.ply (Stanford PLY) and camera_poses.json.
 *
 * This bridge operates in two modes:
 *   --mode=subprocess  : Writes COLMAP CLI invocation commands to stdout for
 *                        the Python pipeline to execute via subprocess.
 *   --mode=validate    : Reads COLMAP output binary/text models and validates
 *                        reconstruction quality, emitting a JSON report.
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <unordered_map>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <stdexcept>
#include <iomanip>
#include <cassert>
#include <cstdint>
#include <filesystem>

namespace fs = std::filesystem;

namespace vastu {
namespace sfm {

// ---------------------------------------------------------------------------
// Data Structures
// ---------------------------------------------------------------------------

struct Point3D {
    uint64_t point3d_id;
    double   x, y, z;
    uint8_t  r, g, b;
    double   error;           // Mean reprojection error (pixels)
    int      num_observations;
};

struct Camera {
    uint32_t    camera_id;
    std::string model;        // "PINHOLE", "RADIAL", etc.
    uint32_t    width;
    uint32_t    height;
    double      fx, fy, cx, cy;
    double      k1, k2;       // Distortion (zeroed for PINHOLE)
};

struct Image {
    uint32_t    image_id;
    std::string file_name;
    uint32_t    camera_id;
    double      qw, qx, qy, qz;  // Quaternion rotation (world-to-camera)
    double      tx, ty, tz;       // Translation (world-to-camera)
    bool        registered;
    int         num_observations;
};

struct ReconstructionStats {
    int    num_images_total;
    int    num_images_registered;
    int    num_sparse_points;
    int    num_observations;
    double mean_reprojection_error_px;
    double registration_ratio;          // registered / total
    bool   reconstruction_valid;
    std::string reconstruction_status;  // "VALID", "SPARSE", "DEGENERATE", "FAILED"
};

// ---------------------------------------------------------------------------
// COLMAP Text Model Parser
// ---------------------------------------------------------------------------

/**
 * Parses COLMAP text-format cameras.txt
 * Format: CAMERA_ID MODEL WIDTH HEIGHT PARAMS...
 */
class ColmapTextModelParser {
public:

    static std::vector<Camera> parse_cameras(const std::string& cameras_txt_path) {
        std::vector<Camera> cameras;
        std::ifstream ifs(cameras_txt_path);
        if (!ifs.is_open()) {
            throw std::runtime_error("Cannot open cameras.txt: " + cameras_txt_path);
        }

        std::string line;
        while (std::getline(ifs, line)) {
            if (line.empty() || line[0] == '#') continue;
            std::istringstream ss(line);

            Camera cam;
            cam.k1 = 0.0; cam.k2 = 0.0;
            ss >> cam.camera_id >> cam.model >> cam.width >> cam.height;

            if (cam.model == "PINHOLE") {
                ss >> cam.fx >> cam.fy >> cam.cx >> cam.cy;
            } else if (cam.model == "SIMPLE_PINHOLE") {
                double f;
                ss >> f >> cam.cx >> cam.cy;
                cam.fx = f; cam.fy = f;
            } else if (cam.model == "RADIAL") {
                ss >> cam.fx >> cam.cx >> cam.cy >> cam.k1 >> cam.k2;
                cam.fy = cam.fx;
            } else {
                // Generic fallback: attempt to read fx fy cx cy
                ss >> cam.fx >> cam.fy >> cam.cx >> cam.cy;
            }
            cameras.push_back(cam);
        }
        return cameras;
    }

    /**
     * Parses COLMAP text-format images.txt
     * Format (interleaved two-line records):
     *   IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME
     *   POINTS2D[] as (X Y POINT3D_ID)
     */
    static std::vector<Image> parse_images(const std::string& images_txt_path) {
        std::vector<Image> images;
        std::ifstream ifs(images_txt_path);
        if (!ifs.is_open()) {
            throw std::runtime_error("Cannot open images.txt: " + images_txt_path);
        }

        std::string line;
        while (std::getline(ifs, line)) {
            if (line.empty() || line[0] == '#') continue;

            std::istringstream ss(line);
            Image img;
            ss >> img.image_id
               >> img.qw >> img.qx >> img.qy >> img.qz
               >> img.tx >> img.ty >> img.tz
               >> img.camera_id
               >> img.file_name;
            img.registered = true;
            img.num_observations = 0;

            // Read the associated 2D point line
            std::string point_line;
            if (std::getline(ifs, point_line)) {
                std::istringstream ps(point_line);
                double px, py;
                int64_t pid;
                while (ps >> px >> py >> pid) {
                    if (pid >= 0) img.num_observations++;
                }
            }
            images.push_back(img);
        }
        return images;
    }

    /**
     * Parses COLMAP text-format points3D.txt
     * Format: POINT3D_ID X Y Z R G B ERROR TRACK[]
     */
    static std::vector<Point3D> parse_points3d(const std::string& points3d_txt_path) {
        std::vector<Point3D> points;
        std::ifstream ifs(points3d_txt_path);
        if (!ifs.is_open()) {
            throw std::runtime_error("Cannot open points3D.txt: " + points3d_txt_path);
        }

        std::string line;
        while (std::getline(ifs, line)) {
            if (line.empty() || line[0] == '#') continue;
            std::istringstream ss(line);

            Point3D pt;
            int r_int, g_int, b_int;
            ss >> pt.point3d_id
               >> pt.x >> pt.y >> pt.z
               >> r_int >> g_int >> b_int
               >> pt.error;

            pt.r = static_cast<uint8_t>(r_int);
            pt.g = static_cast<uint8_t>(g_int);
            pt.b = static_cast<uint8_t>(b_int);
            pt.num_observations = 0;

            // Count track length (image_id feature_id pairs)
            uint32_t img_id, feat_id;
            while (ss >> img_id >> feat_id) {
                pt.num_observations++;
            }
            points.push_back(pt);
        }
        return points;
    }
};

// ---------------------------------------------------------------------------
// Reconstruction Validator
// ---------------------------------------------------------------------------

class ReconstructionValidator {
public:

    static ReconstructionStats compute_stats(
        const std::vector<Image>&   images,
        const std::vector<Point3D>& points3d,
        int total_images_in_dataset
    ) {
        ReconstructionStats stats;
        stats.num_images_total = total_images_in_dataset;
        stats.num_images_registered = static_cast<int>(images.size());
        stats.num_sparse_points = static_cast<int>(points3d.size());

        int total_observations = 0;
        for (const auto& img : images) {
            total_observations += img.num_observations;
        }
        stats.num_observations = total_observations;

        // Mean reprojection error
        if (!points3d.empty()) {
            double sum_error = 0.0;
            for (const auto& pt : points3d) {
                sum_error += pt.error;
            }
            stats.mean_reprojection_error_px = sum_error / points3d.size();
        } else {
            stats.mean_reprojection_error_px = 0.0;
        }

        stats.registration_ratio =
            (total_images_in_dataset > 0)
            ? static_cast<double>(images.size()) / total_images_in_dataset
            : 0.0;

        // Quality classification
        if (points3d.empty() || images.empty()) {
            stats.reconstruction_valid  = false;
            stats.reconstruction_status = "FAILED";
        } else if (stats.registration_ratio < 0.5) {
            stats.reconstruction_valid  = false;
            stats.reconstruction_status = "DEGENERATE";
        } else if (stats.num_sparse_points < 100) {
            stats.reconstruction_valid  = false;
            stats.reconstruction_status = "SPARSE";
        } else if (stats.mean_reprojection_error_px > 4.0) {
            stats.reconstruction_valid  = false;
            stats.reconstruction_status = "DEGENERATE";
        } else {
            stats.reconstruction_valid  = true;
            stats.reconstruction_status = "VALID";
        }

        return stats;
    }

    /**
     * Validates coordinate sanity: no NaN, no Inf, reasonable world bounds.
     */
    static bool validate_point_coordinates(const std::vector<Point3D>& points3d) {
        for (const auto& pt : points3d) {
            if (!std::isfinite(pt.x) || !std::isfinite(pt.y) || !std::isfinite(pt.z)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Validates that reprojection errors are within acceptable bounds.
     * COLMAP bundle adjustment typically achieves <2px for indoor scenes.
     */
    static bool validate_reprojection_errors(
        const std::vector<Point3D>& points3d,
        double max_allowed_error_px = 4.0
    ) {
        for (const auto& pt : points3d) {
            if (pt.error > max_allowed_error_px) {
                return false;
            }
        }
        return true;
    }
};

// ---------------------------------------------------------------------------
// PLY Exporter (Sparse Point Cloud)
// ---------------------------------------------------------------------------

class SparsePLYExporter {
public:

    /**
     * Exports COLMAP sparse 3D points to Stanford PLY format.
     * Output: sparse_points3D.ply
     */
    static bool export_sparse_ply(
        const std::vector<Point3D>& points3d,
        const std::string&          output_path
    ) {
        std::ofstream ofs(output_path);
        if (!ofs.is_open()) return false;

        ofs << "ply\n";
        ofs << "format ascii 1.0\n";
        ofs << "comment VASTU SfM Sparse Point Cloud\n";
        ofs << "element vertex " << points3d.size() << "\n";
        ofs << "property float x\n";
        ofs << "property float y\n";
        ofs << "property float z\n";
        ofs << "property uchar red\n";
        ofs << "property uchar green\n";
        ofs << "property uchar blue\n";
        ofs << "property float reprojection_error\n";
        ofs << "property int num_observations\n";
        ofs << "end_header\n";

        ofs << std::fixed << std::setprecision(5);
        for (const auto& pt : points3d) {
            ofs << static_cast<float>(pt.x) << " "
                << static_cast<float>(pt.y) << " "
                << static_cast<float>(pt.z) << " "
                << static_cast<int>(pt.r)   << " "
                << static_cast<int>(pt.g)   << " "
                << static_cast<int>(pt.b)   << " "
                << static_cast<float>(pt.error) << " "
                << pt.num_observations  << "\n";
        }
        return true;
    }
};

// ---------------------------------------------------------------------------
// JSON Report Writer
// ---------------------------------------------------------------------------

class SfMReportWriter {
public:

    static bool write_reconstruction_report(
        const ReconstructionStats& stats,
        const std::vector<Camera>& cameras,
        const std::string&         output_path
    ) {
        std::ofstream ofs(output_path);
        if (!ofs.is_open()) return false;

        ofs << "{\n";
        ofs << "  \"reconstruction_status\": \"" << stats.reconstruction_status << "\",\n";
        ofs << "  \"reconstruction_valid\": " << (stats.reconstruction_valid ? "true" : "false") << ",\n";
        ofs << "  \"num_images_total\": "       << stats.num_images_total << ",\n";
        ofs << "  \"num_images_registered\": "  << stats.num_images_registered << ",\n";
        ofs << "  \"num_sparse_points\": "      << stats.num_sparse_points << ",\n";
        ofs << "  \"num_observations\": "       << stats.num_observations << ",\n";
        ofs << "  \"mean_reprojection_error_px\": " << std::fixed << std::setprecision(4)
            << stats.mean_reprojection_error_px << ",\n";
        ofs << "  \"registration_ratio\": "     << std::setprecision(4)
            << stats.registration_ratio << ",\n";

        // Camera intrinsics summary
        ofs << "  \"cameras\": [\n";
        for (size_t i = 0; i < cameras.size(); ++i) {
            const auto& cam = cameras[i];
            ofs << "    {\n";
            ofs << "      \"camera_id\": " << cam.camera_id << ",\n";
            ofs << "      \"model\": \""   << cam.model     << "\",\n";
            ofs << "      \"width\": "     << cam.width     << ",\n";
            ofs << "      \"height\": "    << cam.height    << ",\n";
            ofs << "      \"fx\": "        << std::setprecision(4) << cam.fx << ",\n";
            ofs << "      \"fy\": "        << cam.fy << ",\n";
            ofs << "      \"cx\": "        << cam.cx << ",\n";
            ofs << "      \"cy\": "        << cam.cy << ",\n";
            ofs << "      \"k1\": "        << cam.k1 << ",\n";
            ofs << "      \"k2\": "        << cam.k2 << "\n";
            ofs << "    }" << (i + 1 < cameras.size() ? "," : "") << "\n";
        }
        ofs << "  ]\n";
        ofs << "}\n";
        return true;
    }
};

// ---------------------------------------------------------------------------
// COLMAP CLI Command Generator
// ---------------------------------------------------------------------------

/**
 * Generates COLMAP CLI commands for subprocess execution by the Python pipeline.
 * This avoids requiring a full COLMAP C++ library linkage in the build system.
 * The Python sfm_pipeline.py calls these commands via subprocess.
 */
class ColmapCommandGenerator {
public:

    static void print_feature_extraction_cmd(
        const std::string& image_path,
        const std::string& database_path,
        const std::string& camera_model = "PINHOLE"
    ) {
        std::cout << "colmap feature_extractor"
                  << " --image_path "    << image_path
                  << " --database_path " << database_path
                  << " --ImageReader.camera_model " << camera_model
                  << " --ImageReader.single_camera 1"
                  << " --SiftExtraction.use_gpu 1"
                  << " --SiftExtraction.max_num_features 8192"
                  << "\n";
    }

    static void print_exhaustive_matcher_cmd(const std::string& database_path) {
        std::cout << "colmap exhaustive_matcher"
                  << " --database_path " << database_path
                  << " --SiftMatching.use_gpu 1"
                  << "\n";
    }

    static void print_sequential_matcher_cmd(const std::string& database_path, int overlap = 10) {
        std::cout << "colmap sequential_matcher"
                  << " --database_path "                   << database_path
                  << " --SequentialMatching.overlap "      << overlap
                  << " --SequentialMatching.loop_detection 1"
                  << " --SiftMatching.use_gpu 1"
                  << "\n";
    }

    static void print_mapper_cmd(
        const std::string& database_path,
        const std::string& image_path,
        const std::string& output_path
    ) {
        std::cout << "colmap mapper"
                  << " --database_path " << database_path
                  << " --image_path "    << image_path
                  << " --output_path "   << output_path
                  << " --Mapper.num_threads 4"
                  << " --Mapper.init_min_num_inliers 25"
                  << " --Mapper.abs_pose_min_num_inliers 15"
                  << " --Mapper.filter_max_reproj_error 4.0"
                  << "\n";
    }

    static void print_bundle_adjuster_cmd(
        const std::string& input_path,
        const std::string& output_path
    ) {
        std::cout << "colmap bundle_adjuster"
                  << " --input_path "  << input_path
                  << " --output_path " << output_path
                  << " --BundleAdjustment.refine_focal_length 1"
                  << " --BundleAdjustment.refine_principal_point 0"
                  << " --BundleAdjustment.refine_extra_params 0"
                  << "\n";
    }

    static void print_model_converter_cmd(
        const std::string& input_path,
        const std::string& output_path,
        const std::string& output_type = "TXT"
    ) {
        std::cout << "colmap model_converter"
                  << " --input_path "  << input_path
                  << " --output_path " << output_path
                  << " --output_type " << output_type
                  << "\n";
    }
};

// ---------------------------------------------------------------------------
// Validate Mode Entry Point
// ---------------------------------------------------------------------------

static int run_validate_mode(
    const std::string& model_txt_dir,
    const std::string& output_report_path,
    const std::string& output_ply_path,
    int total_images
) {
    std::cout << "[VASTU SfM Bridge] Validating COLMAP reconstruction in: " << model_txt_dir << "\n";

    // Parse model
    auto cameras = ColmapTextModelParser::parse_cameras(model_txt_dir + "/cameras.txt");
    auto images  = ColmapTextModelParser::parse_images (model_txt_dir + "/images.txt");
    auto points  = ColmapTextModelParser::parse_points3d(model_txt_dir + "/points3D.txt");

    std::cout << "[VASTU SfM Bridge] Parsed: "
              << cameras.size() << " cameras, "
              << images.size()  << " registered images, "
              << points.size()  << " sparse 3D points\n";

    // Coordinate validation
    bool coords_valid = ReconstructionValidator::validate_point_coordinates(points);
    if (!coords_valid) {
        std::cerr << "[VASTU SfM Bridge] ERROR: Non-finite coordinates detected in sparse point cloud.\n";
        return 1;
    }

    // Reprojection error validation
    bool reproj_valid = ReconstructionValidator::validate_reprojection_errors(points, 4.0);
    if (!reproj_valid) {
        std::cerr << "[VASTU SfM Bridge] WARNING: Some points exceed reprojection error threshold.\n";
        // Do not abort — record in report
    }

    // Compute quality statistics
    auto stats = ReconstructionValidator::compute_stats(images, points, total_images);

    std::cout << "[VASTU SfM Bridge] Status: " << stats.reconstruction_status
              << " | Registered: " << stats.num_images_registered << "/" << stats.num_images_total
              << " | Points: " << stats.num_sparse_points
              << " | Mean ReProjErr: " << std::fixed << std::setprecision(3)
              << stats.mean_reprojection_error_px << "px\n";

    // Export sparse PLY
    if (!output_ply_path.empty()) {
        bool ply_ok = SparsePLYExporter::export_sparse_ply(points, output_ply_path);
        if (ply_ok) {
            std::cout << "[VASTU SfM Bridge] Sparse PLY written: " << output_ply_path << "\n";
        } else {
            std::cerr << "[VASTU SfM Bridge] ERROR: Failed to write sparse PLY.\n";
            return 1;
        }
    }

    // Write JSON report
    if (!output_report_path.empty()) {
        bool report_ok = SfMReportWriter::write_reconstruction_report(stats, cameras, output_report_path);
        if (report_ok) {
            std::cout << "[VASTU SfM Bridge] Report written: " << output_report_path << "\n";
        } else {
            std::cerr << "[VASTU SfM Bridge] ERROR: Failed to write reconstruction report.\n";
            return 1;
        }
    }

    return stats.reconstruction_valid ? 0 : 2;
}

// ---------------------------------------------------------------------------
// Subprocess Mode Entry Point
// ---------------------------------------------------------------------------

static int run_subprocess_mode(
    const std::string& image_path,
    const std::string& database_path,
    const std::string& sparse_output_path,
    const std::string& camera_model,
    bool use_sequential_matcher
) {
    std::cout << "# VASTU COLMAP Pipeline Commands (subprocess mode)\n";
    std::cout << "# Execute these commands in order to perform full SfM reconstruction.\n\n";

    ColmapCommandGenerator::print_feature_extraction_cmd(image_path, database_path, camera_model);
    std::cout << "\n";

    if (use_sequential_matcher) {
        ColmapCommandGenerator::print_sequential_matcher_cmd(database_path);
    } else {
        ColmapCommandGenerator::print_exhaustive_matcher_cmd(database_path);
    }
    std::cout << "\n";

    ColmapCommandGenerator::print_mapper_cmd(database_path, image_path, sparse_output_path + "/0");
    std::cout << "\n";

    ColmapCommandGenerator::print_bundle_adjuster_cmd(
        sparse_output_path + "/0",
        sparse_output_path + "/0_ba"
    );
    std::cout << "\n";

    ColmapCommandGenerator::print_model_converter_cmd(
        sparse_output_path + "/0_ba",
        sparse_output_path + "/txt",
        "TXT"
    );
    std::cout << "\n";

    return 0;
}

} // namespace sfm
} // namespace vastu

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int main(int argc, char* argv[]) {
    using namespace vastu::sfm;

    // Default mode: print build verification and exit 0
    if (argc < 2) {
        std::cout << "VASTU C++ SfM COLMAP Bridge v1.0 compiled successfully.\n";
        std::cout << "Usage:\n";
        std::cout << "  --mode=subprocess  --image_path=<dir> --database_path=<db> "
                     "--sparse_output=<dir> [--camera_model=PINHOLE] [--sequential]\n";
        std::cout << "  --mode=validate    --model_dir=<txt_model_dir> --total_images=N "
                     "[--output_ply=<path>] [--output_report=<path>]\n";
        return 0;
    }

    // Argument parsing
    std::string mode;
    std::string image_path, database_path, sparse_output, camera_model = "PINHOLE";
    std::string model_dir, output_ply, output_report;
    int total_images = 0;
    bool use_sequential = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        auto eq = arg.find('=');
        if (eq == std::string::npos) {
            if (arg == "--sequential") use_sequential = true;
            continue;
        }
        std::string key = arg.substr(0, eq);
        std::string val = arg.substr(eq + 1);

        if      (key == "--mode")           mode          = val;
        else if (key == "--image_path")     image_path    = val;
        else if (key == "--database_path")  database_path = val;
        else if (key == "--sparse_output")  sparse_output = val;
        else if (key == "--camera_model")   camera_model  = val;
        else if (key == "--model_dir")      model_dir     = val;
        else if (key == "--output_ply")     output_ply    = val;
        else if (key == "--output_report")  output_report = val;
        else if (key == "--total_images")   total_images  = std::stoi(val);
    }

    if (mode == "subprocess") {
        if (image_path.empty() || database_path.empty() || sparse_output.empty()) {
            std::cerr << "ERROR: --mode=subprocess requires --image_path, --database_path, --sparse_output\n";
            return 1;
        }
        return run_subprocess_mode(image_path, database_path, sparse_output, camera_model, use_sequential);

    } else if (mode == "validate") {
        if (model_dir.empty()) {
            std::cerr << "ERROR: --mode=validate requires --model_dir\n";
            return 1;
        }
        return run_validate_mode(model_dir, output_report, output_ply, total_images);

    } else {
        std::cerr << "ERROR: Unknown mode '" << mode << "'. Use --mode=subprocess or --mode=validate\n";
        return 1;
    }
}

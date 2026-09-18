#!/usr/bin/env python3
import os
import uuid

def gen_id():
    return uuid.uuid4().hex[:24].upper()

def main():
    ios_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ios"))
    app_dir = os.path.join(ios_dir, "VastuSpatial")
    proj_dir = os.path.join(ios_dir, "VastuSpatial.xcodeproj")
    os.makedirs(proj_dir, exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "xcshareddata", "xcschemes"), exist_ok=True)

    # Subgroups mapping
    subfolders = ["Camera", "Models", "Network", "Sensors", "Storage", "Upload", "Views"]
    
    file_refs = {}
    build_files = {}

    # Discover files
    subfolder_files = {sf: [] for sf in subfolders}
    root_files = []

    for root, dirs, files in os.walk(app_dir):
        dirs.sort()
        for f in sorted(files):
            if f.endswith(".swift") or f.endswith(".plist"):
                full_path = os.path.join(root, f)
                rel_from_app = os.path.relpath(full_path, app_dir)
                rel_from_ios = os.path.relpath(full_path, ios_dir)
                
                fid = gen_id()
                bid = gen_id() if f.endswith(".swift") else None
                file_refs[rel_from_ios] = (fid, f)
                if bid:
                    build_files[rel_from_ios] = bid

                parts = rel_from_app.split(os.sep)
                if len(parts) > 1 and parts[0] in subfolders:
                    subfolder_files[parts[0]].append((fid, f, rel_from_ios))
                else:
                    root_files.append((fid, f, rel_from_ios))

    # Project IDs
    proj_id = gen_id()
    main_group_id = gen_id()
    app_group_id = gen_id()
    products_group_id = gen_id()
    app_product_fid = gen_id()
    target_id = gen_id()
    sources_build_phase_id = gen_id()
    frameworks_build_phase_id = gen_id()
    resources_build_phase_id = gen_id()
    
    proj_debug_cfg_id = gen_id()
    proj_release_cfg_id = gen_id()
    proj_cfg_list_id = gen_id()
    
    target_debug_cfg_id = gen_id()
    target_release_cfg_id = gen_id()
    target_cfg_list_id = gen_id()

    subgroup_ids = {sf: gen_id() for sf in subfolders}

    lines = [
        "// !$*UTF8*$!",
        "{",
        "\tarchiveVersion = 1;",
        "\tclasses = {",
        "\t};",
        "\tobjectVersion = 56;",
        "\tobjects = {",
        "",
        "/* Begin PBXBuildFile section */"
    ]

    for rel_path, bid in build_files.items():
        fid, fname = file_refs[rel_path]
        lines.append(f"\t\t{bid} /* {fname} in Sources */ = {{isa = PBXBuildFile; fileRef = {fid} /* {fname} */; }};")
    lines.append("/* End PBXBuildFile section */\n")

    lines.append("/* Begin PBXFileReference section */")
    lines.append(f"\t\t{app_product_fid} /* VastuSpatial.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = VastuSpatial.app; sourceTree = BUILT_PRODUCTS_DIR; }};")
    for rel_path, (fid, fname) in file_refs.items():
        ftype = "sourcecode.swift" if fname.endswith(".swift") else "text.plist.xml"
        lines.append(f"\t\t{fid} /* {fname} */ = {{isa = PBXFileReference; lastKnownFileType = {ftype}; name = \"{fname}\"; path = \"{rel_path}\"; sourceTree = \"<group>\"; }};")
    lines.append("/* End PBXFileReference section */\n")

    lines.append("/* Begin PBXFrameworksBuildPhase section */")
    lines.append(f"\t\t{frameworks_build_phase_id} /* Frameworks */ = {{")
    lines.append("\t\t\tisa = PBXFrameworksBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append("/* End PBXFrameworksBuildPhase section */\n")

    lines.append("/* Begin PBXGroup section */")
    # Main group
    lines.append(f"\t\t{main_group_id} = {{")
    lines.append("\t\t\tisa = PBXGroup;")
    lines.append("\t\t\tchildren = (")
    lines.append(f"\t\t\t\t{app_group_id} /* VastuSpatial */,")
    lines.append(f"\t\t\t\t{products_group_id} /* Products */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tsourceTree = \"<group>\";")
    lines.append("\t\t};")

    # Subgroups
    for sf in subfolders:
        gid = subgroup_ids[sf]
        lines.append(f"\t\t{gid} /* {sf} */ = {{")
        lines.append("\t\t\tisa = PBXGroup;")
        lines.append("\t\t\tchildren = (")
        for fid, fname, _ in subfolder_files[sf]:
            lines.append(f"\t\t\t\t{fid} /* {fname} */,")
        lines.append("\t\t\t);")
        lines.append(f"\t\t\tname = {sf};")
        lines.append("\t\t\tsourceTree = \"<group>\";")
        lines.append("\t\t};")

    # VastuSpatial App group
    lines.append(f"\t\t{app_group_id} /* VastuSpatial */ = {{")
    lines.append("\t\t\tisa = PBXGroup;")
    lines.append("\t\t\tchildren = (")
    for fid, fname, _ in root_files:
        lines.append(f"\t\t\t\t{fid} /* {fname} */,")
    for sf in subfolders:
        lines.append(f"\t\t\t\t{subgroup_ids[sf]} /* {sf} */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tname = VastuSpatial;")
    lines.append("\t\t\tsourceTree = \"<group>\";")
    lines.append("\t\t};")

    # Products group
    lines.append(f"\t\t{products_group_id} /* Products */ = {{")
    lines.append("\t\t\tisa = PBXGroup;")
    lines.append("\t\t\tchildren = (")
    lines.append(f"\t\t\t\t{app_product_fid} /* VastuSpatial.app */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tname = Products;")
    lines.append("\t\t\tsourceTree = \"<group>\";")
    lines.append("\t\t};")
    lines.append("/* End PBXGroup section */\n")

    lines.append("/* Begin PBXNativeTarget section */")
    lines.append(f"\t\t{target_id} /* VastuSpatial */ = {{")
    lines.append("\t\t\tisa = PBXNativeTarget;")
    lines.append(f"\t\t\tbuildConfigurationList = {target_cfg_list_id} /* Build configuration list for PBXNativeTarget \"VastuSpatial\" */;")
    lines.append("\t\t\tbuildPhases = (")
    lines.append(f"\t\t\t\t{sources_build_phase_id} /* Sources */,")
    lines.append(f"\t\t\t\t{frameworks_build_phase_id} /* Frameworks */,")
    lines.append(f"\t\t\t\t{resources_build_phase_id} /* Resources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tbuildRules = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tdependencies = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tname = VastuSpatial;")
    lines.append(f"\t\t\tproductName = VastuSpatial;")
    lines.append(f"\t\t\tproductReference = {app_product_fid} /* VastuSpatial.app */;")
    lines.append("\t\t\tproductType = \"com.apple.product-type.application\";")
    lines.append("\t\t};")
    lines.append("/* End PBXNativeTarget section */\n")

    lines.append("/* Begin PBXProject section */")
    lines.append(f"\t\t{proj_id} /* Project object */ = {{")
    lines.append("\t\t\tisa = PBXProject;")
    lines.append("\t\t\tattributes = {")
    lines.append("\t\t\t\tBuildIndependentTargetsInParallel = 1;")
    lines.append("\t\t\t\tLastUpgradeCheck = 1600;")
    lines.append("\t\t\t\tTargetAttributes = {")
    lines.append(f"\t\t\t\t\t{target_id} = {{")
    lines.append("\t\t\t\t\t\tCreatedOnToolsVersion = 16.0;")
    lines.append("\t\t\t\t\t};")
    lines.append("\t\t\t\t};")
    lines.append("\t\t\t};")
    lines.append(f"\t\t\tbuildConfigurationList = {proj_cfg_list_id} /* Build configuration list for PBXProject \"VastuSpatial\" */;")
    lines.append("\t\t\tcompatibilityVersion = \"Xcode 14.0\";")
    lines.append("\t\t\tdevelopmentRegion = en;")
    lines.append("\t\t\thasScannedForEncodings = 0;")
    lines.append("\t\t\tknownRegions = (")
    lines.append("\t\t\t\ten,")
    lines.append("\t\t\t\tBase,")
    lines.append("\t\t\t);")
    lines.append(f"\t\t\tmainGroup = {main_group_id};")
    lines.append(f"\t\t\tproductRefGroup = {products_group_id} /* Products */;")
    lines.append("\t\t\tprojectDirPath = \"\";")
    lines.append("\t\t\tprojectRoot = \"\";")
    lines.append("\t\t\ttargets = (")
    lines.append(f"\t\t\t\t{target_id} /* VastuSpatial */,")
    lines.append("\t\t\t);")
    lines.append("\t\t};")
    lines.append("/* End PBXProject section */\n")

    lines.append("/* Begin PBXResourcesBuildPhase section */")
    lines.append(f"\t\t{resources_build_phase_id} /* Resources */ = {{")
    lines.append("\t\t\tisa = PBXResourcesBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append("/* End PBXResourcesBuildPhase section */\n")

    lines.append("/* Begin PBXSourcesBuildPhase section */")
    lines.append(f"\t\t{sources_build_phase_id} /* Sources */ = {{")
    lines.append("\t\t\tisa = PBXSourcesBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    for rel_path, bid in build_files.items():
        fname = file_refs[rel_path][1]
        lines.append(f"\t\t\t\t{bid} /* {fname} in Sources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append("/* End PBXSourcesBuildPhase section */\n")

    # Project XCBuildConfiguration
    lines.append("/* Begin XCBuildConfiguration section */")
    lines.append(f"\t\t{proj_debug_cfg_id} /* Debug */ = {{")
    lines.append("\t\t\tisa = XCBuildConfiguration;")
    lines.append("\t\t\tbuildSettings = {")
    lines.append("\t\t\t\tALWAYS_SEARCH_USER_PATHS = NO;")
    lines.append("\t\t\t\tCLANG_ANALYZER_NONNULL = YES;")
    lines.append("\t\t\t\tCLANG_ENABLE_MODULES = YES;")
    lines.append("\t\t\t\tCOPY_PHASE_STRIP = NO;")
    lines.append("\t\t\t\tDEBUG_INFORMATION_FORMAT = dwarf;")
    lines.append("\t\t\t\tENABLE_STRICT_OBJC_MSGSEND = YES;")
    lines.append("\t\t\t\tENABLE_TESTABILITY = YES;")
    lines.append("\t\t\t\tGCC_DYNAMIC_NO_PIC = NO;")
    lines.append("\t\t\t\tGCC_OPTIMIZATION_LEVEL = 0;")
    lines.append("\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = (")
    lines.append("\t\t\t\t\t\"DEBUG=1\",")
    lines.append("\t\t\t\t\t\"$(inherited)\",")
    lines.append("\t\t\t\t);")
    lines.append("\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;")
    lines.append("\t\t\t\tMTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;")
    lines.append("\t\t\t\tONLY_ACTIVE_ARCH = YES;")
    lines.append("\t\t\t\tSDKROOT = iphoneos;")
    lines.append("\t\t\t\tSWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;")
    lines.append("\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = \"-Onone\";")
    lines.append("\t\t\t\tSWIFT_VERSION = 5.0;")
    lines.append("\t\t\t};")
    lines.append("\t\t\tname = Debug;")
    lines.append("\t\t};")

    lines.append(f"\t\t{proj_release_cfg_id} /* Release */ = {{")
    lines.append("\t\t\tisa = XCBuildConfiguration;")
    lines.append("\t\t\tbuildSettings = {")
    lines.append("\t\t\t\tALWAYS_SEARCH_USER_PATHS = NO;")
    lines.append("\t\t\t\tCLANG_ANALYZER_NONNULL = YES;")
    lines.append("\t\t\t\tCLANG_ENABLE_MODULES = YES;")
    lines.append("\t\t\t\tCOPY_PHASE_STRIP = NO;")
    lines.append("\t\t\t\tDEBUG_INFORMATION_FORMAT = \"dwarf-with-dsym\";")
    lines.append("\t\t\t\tENABLE_NS_ASSERTIONS = NO;")
    lines.append("\t\t\t\tENABLE_STRICT_OBJC_MSGSEND = YES;")
    lines.append("\t\t\t\tGCC_OPTIMIZATION_LEVEL = s;")
    lines.append("\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;")
    lines.append("\t\t\t\tMTL_ENABLE_DEBUG_INFO = NO;")
    lines.append("\t\t\t\tSDKROOT = iphoneos;")
    lines.append("\t\t\t\tSWIFT_COMPILATION_MODE = wholemodule;")
    lines.append("\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = \"-O\";")
    lines.append("\t\t\t\tSWIFT_VERSION = 5.0;")
    lines.append("\t\t\t\tVALIDATE_PRODUCT = YES;")
    lines.append("\t\t\t};")
    lines.append("\t\t\tname = Release;")
    lines.append("\t\t};")

    # Target XCBuildConfiguration
    lines.append(f"\t\t{target_debug_cfg_id} /* Debug */ = {{")
    lines.append("\t\t\tisa = XCBuildConfiguration;")
    lines.append("\t\t\tbuildSettings = {")
    lines.append("\t\t\t\tASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;")
    lines.append("\t\t\t\tCODE_SIGN_STYLE = Automatic;")
    lines.append("\t\t\t\tCURRENT_PROJECT_VERSION = 1;")
    lines.append("\t\t\t\tDEVELOPMENT_TEAM = \"\";")
    lines.append("\t\t\t\tGENERATE_INFOPLIST_FILE = NO;")
    lines.append("\t\t\t\tINFOPLIST_FILE = VastuSpatial/Info.plist;")
    lines.append("\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;")
    lines.append("\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (")
    lines.append("\t\t\t\t\t\"$(inherited)\",")
    lines.append("\t\t\t\t\t\"@executable_path/Frameworks\",")
    lines.append("\t\t\t\t);")
    lines.append("\t\t\t\tMARKETING_VERSION = 1.0.0;")
    lines.append("\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.vastu.spatial;")
    lines.append("\t\t\t\tPRODUCT_NAME = \"$(TARGET_NAME)\";")
    lines.append("\t\t\t\tSWIFT_EMIT_LOC_STRINGS = YES;")
    lines.append("\t\t\t\tSWIFT_VERSION = 5.0;")
    lines.append("\t\t\t\tTARGETED_DEVICE_FAMILY = \"1,2\";")
    lines.append("\t\t\t};")
    lines.append("\t\t\tname = Debug;")
    lines.append("\t\t};")

    lines.append(f"\t\t{target_release_cfg_id} /* Release */ = {{")
    lines.append("\t\t\tisa = XCBuildConfiguration;")
    lines.append("\t\t\tbuildSettings = {")
    lines.append("\t\t\t\tASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;")
    lines.append("\t\t\t\tCODE_SIGN_STYLE = Automatic;")
    lines.append("\t\t\t\tCURRENT_PROJECT_VERSION = 1;")
    lines.append("\t\t\t\tDEVELOPMENT_TEAM = \"\";")
    lines.append("\t\t\t\tGENERATE_INFOPLIST_FILE = NO;")
    lines.append("\t\t\t\tINFOPLIST_FILE = VastuSpatial/Info.plist;")
    lines.append("\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;")
    lines.append("\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (")
    lines.append("\t\t\t\t\t\"$(inherited)\",")
    lines.append("\t\t\t\t\t\"@executable_path/Frameworks\",")
    lines.append("\t\t\t\t);")
    lines.append("\t\t\t\tMARKETING_VERSION = 1.0.0;")
    lines.append("\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.vastu.spatial;")
    lines.append("\t\t\t\tPRODUCT_NAME = \"$(TARGET_NAME)\";")
    lines.append("\t\t\t\tSWIFT_EMIT_LOC_STRINGS = YES;")
    lines.append("\t\t\t\tSWIFT_VERSION = 5.0;")
    lines.append("\t\t\t\tTARGETED_DEVICE_FAMILY = \"1,2\";")
    lines.append("\t\t\t};")
    lines.append("\t\t\tname = Release;")
    lines.append("\t\t};")
    lines.append("/* End XCBuildConfiguration section */\n")

    # XCConfigurationList
    lines.append("/* Begin XCConfigurationList section */")
    lines.append(f"\t\t{proj_cfg_list_id} /* Build configuration list for PBXProject \"VastuSpatial\" */ = {{")
    lines.append("\t\t\tisa = XCConfigurationList;")
    lines.append("\t\t\tbuildConfigurations = (")
    lines.append(f"\t\t\t\t{proj_debug_cfg_id} /* Debug */,")
    lines.append(f"\t\t\t\t{proj_release_cfg_id} /* Release */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tdefaultConfigurationIsVisible = 0;")
    lines.append("\t\t\tdefaultConfigurationName = Release;")
    lines.append("\t\t};")

    lines.append(f"\t\t{target_cfg_list_id} /* Build configuration list for PBXNativeTarget \"VastuSpatial\" */ = {{")
    lines.append("\t\t\tisa = XCConfigurationList;")
    lines.append("\t\t\tbuildConfigurations = (")
    lines.append(f"\t\t\t\t{target_debug_cfg_id} /* Debug */,")
    lines.append(f"\t\t\t\t{target_release_cfg_id} /* Release */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tdefaultConfigurationIsVisible = 0;")
    lines.append("\t\t\tdefaultConfigurationName = Release;")
    lines.append("\t\t};")
    lines.append("/* End XCConfigurationList section */\n")

    lines.append("\t};")
    lines.append(f"\trootObject = {proj_id} /* Project object */;")
    lines.append("}")

    pbxproj_path = os.path.join(proj_dir, "project.pbxproj")
    with open(pbxproj_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Created {pbxproj_path} with structured groups.")

if __name__ == "__main__":
    main()

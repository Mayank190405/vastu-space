// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "VastuSpatial",
    platforms: [
        .iOS(.v17)
    ],
    products: [
        .library(
            name: "VastuSpatial",
            targets: ["VastuSpatial"]),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "VastuSpatial",
            dependencies: [],
            path: "VastuSpatial"
        ),
        .testTarget(
            name: "VastuSpatialTests",
            dependencies: ["VastuSpatial"],
            path: "VastuSpatialTests"
        ),
    ]
)

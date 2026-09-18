package geo

import (
	"database/sql/driver"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"math"
)

// ---------------------------------------------------------------------------
// VĀSTU Indoor Spatial Computing — PostGIS Geometry Types (Go)
//
// This package provides lightweight Go types for reading and writing PostGIS
// geometry values via pgx. All geometries use SRID 0 (local metric cartesian
// coordinate system — not WGS84).
//
// Supported types:
//   - Point3D   → GEOMETRY(POINTZ, 0)
//   - LineString3D → GEOMETRY(LINESTRINGZ, 0)
//   - Envelope3D  → axis-aligned 3D bounding box (used for queries)
// ---------------------------------------------------------------------------

const LocalSRID = 0 // Indoor cartesian coordinate system (meters)

// ---------------------------------------------------------------------------
// Point3D — GEOMETRY(POINTZ, 0)
// ---------------------------------------------------------------------------

// Point3D represents a 3D point in the indoor metric coordinate system.
// X = horizontal, Y = depth, Z = elevation (meters from origin).
type Point3D struct {
	X float64
	Y float64
	Z float64
}

// IsZero returns true if all coordinates are zero.
func (p Point3D) IsZero() bool {
	return p.X == 0 && p.Y == 0 && p.Z == 0
}

// DistanceTo returns the Euclidean 3D distance to another point.
func (p Point3D) DistanceTo(other Point3D) float64 {
	dx := p.X - other.X
	dy := p.Y - other.Y
	dz := p.Z - other.Z
	return math.Sqrt(dx*dx + dy*dy + dz*dz)
}

// WKT returns the Well-Known Text representation for SQL injection.
func (p Point3D) WKT() string {
	return fmt.Sprintf("SRID=%d;POINTZ(%g %g %g)", LocalSRID, p.X, p.Y, p.Z)
}

// Value implements driver.Valuer — writes EWKT for pgx.
func (p Point3D) Value() (driver.Value, error) {
	return p.WKT(), nil
}

// Scan implements sql.Scanner — reads PostGIS EWKB hex from pgx.
func (p *Point3D) Scan(val interface{}) error {
	if val == nil {
		return nil
	}
	switch v := val.(type) {
	case string:
		return p.parseEWKBHex(v)
	case []byte:
		return p.parseEWKBHex(string(v))
	default:
		return fmt.Errorf("geo.Point3D: unsupported scan type %T", val)
	}
}

// parseEWKBHex decodes a PostGIS EWKB hex string into X/Y/Z.
// EWKB layout for POINTZ (type 0x80000001, little-endian):
//   byte[0]   = 0x01 (little-endian flag)
//   uint32[1] = geometry type | WKBZFLAG (0x80000001 for POINTZ)
//   uint32[2] = SRID (present when WKBSRIDFLAG 0x20000000 is set)
//   float64[n] = X, Y, Z
func (p *Point3D) parseEWKBHex(s string) error {
	if s == "" {
		return nil
	}
	b, err := hex.DecodeString(s)
	if err != nil {
		return fmt.Errorf("geo.Point3D: hex decode error: %w", err)
	}
	if len(b) < 5 {
		return fmt.Errorf("geo.Point3D: EWKB too short (%d bytes)", len(b))
	}

	// byte[0]: byte order
	if b[0] != 0x01 {
		return fmt.Errorf("geo.Point3D: only little-endian EWKB supported")
	}
	order := binary.LittleEndian

	geomType := order.Uint32(b[1:5])
	offset := 5

	hasZ    := (geomType & 0x80000000) != 0 || (geomType&0xFFFF) == 1001
	hasSRID := (geomType & 0x20000000) != 0

	if hasSRID {
		offset += 4 // skip SRID uint32
	}

	if len(b) < offset+16 {
		return fmt.Errorf("geo.Point3D: EWKB too short for XY coordinates")
	}

	p.X = math.Float64frombits(order.Uint64(b[offset:]))
	offset += 8
	p.Y = math.Float64frombits(order.Uint64(b[offset:]))
	offset += 8

	if hasZ && len(b) >= offset+8 {
		p.Z = math.Float64frombits(order.Uint64(b[offset:]))
	}

	return nil
}

// NullPoint3D is a nullable 3D point (maps to SQL NULL when not set).
type NullPoint3D struct {
	Point Point3D
	Valid bool
}

func (n NullPoint3D) Value() (driver.Value, error) {
	if !n.Valid {
		return nil, nil
	}
	return n.Point.Value()
}

func (n *NullPoint3D) Scan(val interface{}) error {
	if val == nil {
		n.Valid = false
		return nil
	}
	n.Valid = true
	return n.Point.Scan(val)
}

// ---------------------------------------------------------------------------
// Envelope3D — 3D axis-aligned bounding box (for spatial queries)
// ---------------------------------------------------------------------------

// Envelope3D represents a 3D AABB in local metric space.
type Envelope3D struct {
	MinX, MinY, MinZ float64
	MaxX, MaxY, MaxZ float64
}

// Contains returns true if the point is inside (or on the boundary of) the envelope.
func (e Envelope3D) Contains(p Point3D) bool {
	return p.X >= e.MinX && p.X <= e.MaxX &&
		p.Y >= e.MinY && p.Y <= e.MaxY &&
		p.Z >= e.MinZ && p.Z <= e.MaxZ
}

// Center returns the geometric center of the envelope.
func (e Envelope3D) Center() Point3D {
	return Point3D{
		X: (e.MinX + e.MaxX) / 2,
		Y: (e.MinY + e.MaxY) / 2,
		Z: (e.MinZ + e.MaxZ) / 2,
	}
}

// Volume returns the volume in cubic meters.
func (e Envelope3D) Volume() float64 {
	return (e.MaxX - e.MinX) * (e.MaxY - e.MinY) * (e.MaxZ - e.MinZ)
}

// STMakeEnvelopeExpr returns a PostGIS ST_MakeEnvelope SQL expression string
// for use in parameterized queries as a bounding-box filter geometry.
func (e Envelope3D) STMakeEnvelopeExpr() string {
	return fmt.Sprintf(
		"ST_SetSRID(ST_MakeEnvelope(%g, %g, %g, %g), %d)",
		e.MinX, e.MinY, e.MaxX, e.MaxY, LocalSRID,
	)
}

// ---------------------------------------------------------------------------
// LineString3D — GEOMETRY(LINESTRINGZ, 0)
// ---------------------------------------------------------------------------

// LineString3D represents an ordered sequence of 3D points (e.g., a capture
// trajectory or navigation edge path).
type LineString3D struct {
	Points []Point3D
}

// Length3D returns the total path length in meters.
func (l LineString3D) Length3D() float64 {
	total := 0.0
	for i := 1; i < len(l.Points); i++ {
		total += l.Points[i-1].DistanceTo(l.Points[i])
	}
	return total
}

// WKT returns the EWKT representation for SQL.
func (l LineString3D) WKT() string {
	if len(l.Points) < 2 {
		return ""
	}
	s := fmt.Sprintf("SRID=%d;LINESTRINGZ(", LocalSRID)
	for i, p := range l.Points {
		if i > 0 {
			s += ","
		}
		s += fmt.Sprintf("%g %g %g", p.X, p.Y, p.Z)
	}
	s += ")"
	return s
}

func (l LineString3D) Value() (driver.Value, error) {
	wkt := l.WKT()
	if wkt == "" {
		return nil, nil
	}
	return wkt, nil
}

// ---------------------------------------------------------------------------
// Spatial Query Helpers (SQL fragment builders for use in pgx queries)
// ---------------------------------------------------------------------------

// ST3DDWithin returns a SQL fragment for a 3D radius search.
// Usage: WHERE <geom_col> IS NOT NULL AND <ST3DDWithin(geom_col, $1, $2)>
func ST3DDWithin(geomCol string, x, y, z, radiusM float64) string {
	return fmt.Sprintf(
		"ST_3DDWithin(%s, ST_SetSRID(ST_MakePoint(%g, %g, %g), %d), %g)",
		geomCol, x, y, z, LocalSRID, radiusM,
	)
}

// ST3DDistance returns a SQL expression for the distance from a geometry
// column to a query point.
func ST3DDistance(geomCol string, x, y, z float64) string {
	return fmt.Sprintf(
		"ST_3DDistance(%s, ST_SetSRID(ST_MakePoint(%g, %g, %g), %d))",
		geomCol, x, y, z, LocalSRID,
	)
}

// STMakePoint3D returns a SQL expression for a 3D point literal.
func STMakePoint3D(x, y, z float64) string {
	return fmt.Sprintf(
		"ST_SetSRID(ST_MakePoint(%g, %g, %g), %d)",
		x, y, z, LocalSRID,
	)
}

// KNNOrderBy returns the <-> KNN operator expression for nearest-neighbour
// ordering. Use with ORDER BY + LIMIT for fast approximate nearest node queries.
func KNNOrderBy(geomCol string, x, y, z float64) string {
	return fmt.Sprintf(
		"%s <-> ST_SetSRID(ST_MakePoint(%g, %g, %g), %d)",
		geomCol, x, y, z, LocalSRID,
	)
}

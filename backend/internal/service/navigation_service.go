package service

import (
	"container/heap"
	"context"
	"errors"
	"fmt"
	"math"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type NavigationService struct {
	navRepo repository.NavigationRepository
	poiRepo repository.POIRepository
}

func NewNavigationService(navRepo repository.NavigationRepository, poiRepo repository.POIRepository) *NavigationService {
	return &NavigationService{
		navRepo: navRepo,
		poiRepo: poiRepo,
	}
}

func (s *NavigationService) CreateNode(ctx context.Context, n *domain.NavNode) error {
	return s.navRepo.CreateNode(ctx, n)
}

func (s *NavigationService) CreateEdge(ctx context.Context, e *domain.NavEdge) error {
	return s.navRepo.CreateEdge(ctx, e)
}

func (s *NavigationService) ListNodes(ctx context.Context, projectID uuid.UUID) ([]*domain.NavNode, error) {
	return s.navRepo.ListNodesByProject(ctx, projectID)
}

func (s *NavigationService) ListEdges(ctx context.Context, projectID uuid.UUID) ([]*domain.NavEdge, error) {
	return s.navRepo.ListEdgesByProject(ctx, projectID)
}

// Graph node priority item for Dijkstra / A*
type pathItem struct {
	nodeID   uuid.UUID
	priority float64
	index    int
}

type priorityQueue []*pathItem

func (pq priorityQueue) Len() int           { return len(pq) }
func (pq priorityQueue) Less(i, j int) bool { return pq[i].priority < pq[j].priority }
func (pq priorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
	pq[i].index = i
	pq[j].index = j
}
func (pq *priorityQueue) Push(x interface{}) {
	n := len(*pq)
	item := x.(*pathItem)
	item.index = n
	*pq = append(*pq, item)
}
func (pq *priorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	old[n-1] = nil
	item.index = -1
	*pq = old[0 : n-1]
	return item
}

// Euclidean distance 3D
func distance3D(x1, y1, z1, x2, y2, z2 float64) float64 {
	dx := x1 - x2
	dy := y1 - y2
	dz := z1 - z2
	return math.Sqrt(dx*dx + dy*dy + dz*dz)
}

func (s *NavigationService) CalculateRoute(ctx context.Context, req domain.NavRouteRequest) (*domain.NavRouteResponse, error) {
	if req.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}

	startX, startY, startZ := req.StartPosX, req.StartPosY, req.StartPosZ
	targetX, targetY, targetZ := req.TargetPosX, req.TargetPosY, req.TargetPosZ

	// If POIs are given, override start / target coordinates
	if req.StartPOIID != nil {
		startPOI, err := s.poiRepo.GetByID(ctx, *req.StartPOIID)
		if err == nil && startPOI != nil {
			startX, startY, startZ = startPOI.PosX, startPOI.PosY, startPOI.PosZ
		}
	}
	if req.TargetPOIID != nil {
		targetPOI, err := s.poiRepo.GetByID(ctx, *req.TargetPOIID)
		if err == nil && targetPOI != nil {
			targetX, targetY, targetZ = targetPOI.PosX, targetPOI.PosY, targetPOI.PosZ
		}
	}

	nodes, err := s.navRepo.ListNodesByProject(ctx, req.ProjectID)
	if err != nil {
		return nil, err
	}
	if len(nodes) == 0 {
		// If no dedicated nodes exist, generate a direct line step
		dist := distance3D(startX, startY, startZ, targetX, targetY, targetZ)
		walkSec := int(dist / 1.2) // ~1.2 m/s avg walking speed
		return &domain.NavRouteResponse{
			ProjectID:              req.ProjectID,
			TotalDistanceMeters:    math.Round(dist*100) / 100,
			EstimatedWalkSeconds:   walkSec,
			IsWheelchairAccessible: true,
			Waypoints: []map[string]float64{
				{"x": startX, "y": startY, "z": startZ},
				{"x": targetX, "y": targetY, "z": targetZ},
			},
			Steps: []domain.RouteStep{
				{
					StepIndex:      1,
					Instruction:    fmt.Sprintf("Walk straight for %.1f meters towards your destination", dist),
					TurnType:       "straight",
					DistanceMeters: math.Round(dist*100) / 100,
					FromPosition:   map[string]float64{"x": startX, "y": startY, "z": startZ},
					ToPosition:     map[string]float64{"x": targetX, "y": targetY, "z": targetZ},
				},
				{
					StepIndex:      2,
					Instruction:    "You have arrived at your destination",
					TurnType:       "arrive",
					DistanceMeters: 0,
					FromPosition:   map[string]float64{"x": targetX, "y": targetY, "z": targetZ},
					ToPosition:     map[string]float64{"x": targetX, "y": targetY, "z": targetZ},
				},
			},
		}, nil
	}

	edges, err := s.navRepo.ListEdgesByProject(ctx, req.ProjectID)
	if err != nil {
		return nil, err
	}

	nodeMap := make(map[uuid.UUID]*domain.NavNode)
	for _, n := range nodes {
		nodeMap[n.ID] = n
	}

	// Find nearest node to Start and Target
	var startNode, targetNode *domain.NavNode
	minStartDist := math.MaxFloat64
	minTargetDist := math.MaxFloat64

	for _, n := range nodes {
		if req.RequireWheelchair && !n.IsWheelchairAccessible {
			continue
		}
		sd := distance3D(startX, startY, startZ, n.PosX, n.PosY, n.PosZ)
		if sd < minStartDist {
			minStartDist = sd
			startNode = n
		}
		td := distance3D(targetX, targetY, targetZ, n.PosX, n.PosY, n.PosZ)
		if td < minTargetDist {
			minTargetDist = td
			targetNode = n
		}
	}

	if startNode == nil || targetNode == nil {
		return nil, errors.New("no accessible navigation nodes found near points")
	}

	// Build adjacency list
	type edgeWeight struct {
		toNodeID               uuid.UUID
		distance               float64
		edgeType               domain.NavEdgeType
		isWheelchairAccessible bool
	}
	adj := make(map[uuid.UUID][]edgeWeight)
	for _, e := range edges {
		if req.RequireWheelchair && !e.IsWheelchairAccessible {
			continue
		}
		if req.AvoidStairs && e.EdgeType == domain.NavEdgeTypeStairs {
			continue
		}

		weight := e.DistanceMeters * e.WeightModifier
		adj[e.FromNodeID] = append(adj[e.FromNodeID], edgeWeight{
			toNodeID:               e.ToNodeID,
			distance:               weight,
			edgeType:               e.EdgeType,
			isWheelchairAccessible: e.IsWheelchairAccessible,
		})
		if e.IsBidirectional {
			adj[e.ToNodeID] = append(adj[e.ToNodeID], edgeWeight{
				toNodeID:               e.FromNodeID,
				distance:               weight,
				edgeType:               e.EdgeType,
				isWheelchairAccessible: e.IsWheelchairAccessible,
			})
		}
	}

	// A* / Dijkstra path search
	dist := make(map[uuid.UUID]float64)
	prev := make(map[uuid.UUID]uuid.UUID)
	prevEdge := make(map[uuid.UUID]domain.NavEdgeType)
	for _, n := range nodes {
		dist[n.ID] = math.MaxFloat64
	}
	dist[startNode.ID] = 0

	pq := make(priorityQueue, 0)
	heap.Init(&pq)
	heap.Push(&pq, &pathItem{nodeID: startNode.ID, priority: 0})

	for pq.Len() > 0 {
		top := heap.Pop(&pq).(*pathItem)
		currID := top.nodeID

		if currID == targetNode.ID {
			break
		}

		if top.priority > dist[currID] {
			continue
		}

		for _, edge := range adj[currID] {
			alt := dist[currID] + edge.distance
			if alt < dist[edge.toNodeID] {
				dist[edge.toNodeID] = alt
				prev[edge.toNodeID] = currID
				prevEdge[edge.toNodeID] = edge.edgeType

				// Heuristic for A* towards target
				h := 0.0
				if tNode, ok := nodeMap[edge.toNodeID]; ok {
					h = distance3D(tNode.PosX, tNode.PosY, tNode.PosZ, targetNode.PosX, targetNode.PosY, targetNode.PosZ)
				}

				heap.Push(&pq, &pathItem{nodeID: edge.toNodeID, priority: alt + h})
			}
		}
	}

	// Reconstruct path
	var path []uuid.UUID
	curr := targetNode.ID
	for {
		path = append([]uuid.UUID{curr}, path...)
		p, exists := prev[curr]
		if !exists {
			break
		}
		curr = p
	}

	if len(path) == 0 || path[0] != startNode.ID {
		// Fallback direct path
		d := distance3D(startX, startY, startZ, targetX, targetY, targetZ)
		return &domain.NavRouteResponse{
			ProjectID:              req.ProjectID,
			TotalDistanceMeters:    math.Round(d*100) / 100,
			EstimatedWalkSeconds:   int(d / 1.2),
			IsWheelchairAccessible: true,
			Waypoints: []map[string]float64{
				{"x": startX, "y": startY, "z": startZ},
				{"x": targetX, "y": targetY, "z": targetZ},
			},
			Steps: []domain.RouteStep{
				{
					StepIndex:      1,
					Instruction:    fmt.Sprintf("Walk %.1f meters to target position", d),
					TurnType:       "straight",
					DistanceMeters: math.Round(d*100) / 100,
					FromPosition:   map[string]float64{"x": startX, "y": startY, "z": startZ},
					ToPosition:     map[string]float64{"x": targetX, "y": targetY, "z": targetZ},
				},
				{
					StepIndex:      2,
					Instruction:    "Arrived at destination",
					TurnType:       "arrive",
					DistanceMeters: 0,
					FromPosition:   map[string]float64{"x": targetX, "y": targetY, "z": targetZ},
					ToPosition:     map[string]float64{"x": targetX, "y": targetY, "z": targetZ},
				},
			},
		}, nil
	}

	// Assemble Waypoints and Step instructions
	var waypoints []map[string]float64
	waypoints = append(waypoints, map[string]float64{"x": startX, "y": startY, "z": startZ})

	var steps []domain.RouteStep
	totalDist := distance3D(startX, startY, startZ, startNode.PosX, startNode.PosY, startNode.PosZ)

	// Step 1: Start to first node
	if totalDist > 0.5 {
		steps = append(steps, domain.RouteStep{
			StepIndex:      len(steps) + 1,
			Instruction:    fmt.Sprintf("Head toward navigation corridor (%.1fm)", totalDist),
			TurnType:       "straight",
			DistanceMeters: math.Round(totalDist*100) / 100,
			FromPosition:   map[string]float64{"x": startX, "y": startY, "z": startZ},
			ToPosition:     map[string]float64{"x": startNode.PosX, "y": startNode.PosY, "z": startNode.PosZ},
		})
	}

	for i := 0; i < len(path)-1; i++ {
		u := nodeMap[path[i]]
		v := nodeMap[path[i+1]]
		waypoints = append(waypoints, map[string]float64{"x": u.PosX, "y": u.PosY, "z": u.PosZ})

		segDist := distance3D(u.PosX, u.PosY, u.PosZ, v.PosX, v.PosY, v.PosZ)
		totalDist += segDist

		eType := prevEdge[v.ID]
		instruction := fmt.Sprintf("Follow hallway straight for %.1fm", segDist)
		turnType := "straight"
		var transition *string

		if eType == domain.NavEdgeTypeStairs {
			if v.PosZ > u.PosZ {
				instruction = fmt.Sprintf("Take stairs UP to level above (%.1fm)", segDist)
				turnType = "take_stairs_up"
			} else {
				instruction = fmt.Sprintf("Take stairs DOWN to level below (%.1fm)", segDist)
				turnType = "take_stairs_down"
			}
			t := "staircase"
			transition = &t
		} else if eType == domain.NavEdgeTypeElevator {
			instruction = fmt.Sprintf("Take elevator to next level (%.1fm)", segDist)
			turnType = "take_elevator"
			t := "elevator"
			transition = &t
		} else if eType == domain.NavEdgeTypeDoor {
			instruction = fmt.Sprintf("Pass through doorway (%.1fm)", segDist)
			turnType = "straight"
		}

		steps = append(steps, domain.RouteStep{
			StepIndex:       len(steps) + 1,
			Instruction:     instruction,
			TurnType:        turnType,
			DistanceMeters:  math.Round(segDist*100) / 100,
			FromPosition:    map[string]float64{"x": u.PosX, "y": u.PosY, "z": u.PosZ},
			ToPosition:      map[string]float64{"x": v.PosX, "y": v.PosY, "z": v.PosZ},
			LevelTransition: transition,
		})
	}

	// Last node to target
	targetDist := distance3D(targetNode.PosX, targetNode.PosY, targetNode.PosZ, targetX, targetY, targetZ)
	totalDist += targetDist
	waypoints = append(waypoints, map[string]float64{"x": targetNode.PosX, "y": targetNode.PosY, "z": targetNode.PosZ})
	waypoints = append(waypoints, map[string]float64{"x": targetX, "y": targetY, "z": targetZ})

	if targetDist > 0.5 {
		steps = append(steps, domain.RouteStep{
			StepIndex:      len(steps) + 1,
			Instruction:    fmt.Sprintf("Walk final %.1fm to destination", targetDist),
			TurnType:       "straight",
			DistanceMeters: math.Round(targetDist*100) / 100,
			FromPosition:   map[string]float64{"x": targetNode.PosX, "y": targetNode.PosY, "z": targetNode.PosZ},
			ToPosition:     map[string]float64{"x": targetX, "y": targetY, "z": targetZ},
		})
	}

	// Final destination step
	steps = append(steps, domain.RouteStep{
		StepIndex:      len(steps) + 1,
		Instruction:    "You have arrived at your destination",
		TurnType:       "arrive",
		DistanceMeters: 0,
		FromPosition:   map[string]float64{"x": targetX, "y": targetY, "z": targetZ},
		ToPosition:     map[string]float64{"x": targetX, "y": targetY, "z": targetZ},
	})

	return &domain.NavRouteResponse{
		ProjectID:              req.ProjectID,
		TotalDistanceMeters:    math.Round(totalDist*100) / 100,
		EstimatedWalkSeconds:   int(totalDist / 1.2),
		IsWheelchairAccessible: req.RequireWheelchair,
		Waypoints:              waypoints,
		Steps:                  steps,
	}, nil
}

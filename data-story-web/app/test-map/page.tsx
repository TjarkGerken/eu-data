"use client";

import { InteractiveMap } from "@/components/interactive-map";

export default function MapTestPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Map Component Test - Clusters Layer</h1>
      <div className="space-y-8">
        <div>
          <h2 className="text-xl font-semibold mb-2">Test 1: Interactive Map with Clusters Layer</h2>
          <InteractiveMap
            title="Climate Risk Clusters"
            description="Testing clusters layer display from EPSG:3035 to WGS84"
            selectedLayers={["clusters-slr-current"]}
            height="600px"
            enableLayerControls={true}
            centerLat={51.27}
            centerLng={4.04}
            zoom={10}
            autoFitBounds={true}
          />
        </div>
        
        <div>
          <h2 className="text-xl font-semibold mb-2">Test 2: Map with All Available Layers</h2>
          <InteractiveMap
            title="All Available Layers"
            description="Display all detected layers in the system"
            selectedLayers={[]}
            height="500px"
            enableLayerControls={true}
            centerLat={52.1326}
            centerLng={5.2913}
            zoom={8}
            autoFitBounds={false}
          />
        </div>
      </div>
    </div>
  );
}

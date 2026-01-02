import { useState, useMemo } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from 'react-simple-maps';

// World topology JSON URL
const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

// Continent view configurations
const CONTINENT_VIEWS: Record<string, { center: [number, number]; zoom: number }> = {
  'WORLD': { center: [0, 20], zoom: 1 },
  'EUROPE': { center: [15, 50], zoom: 4 },
  'ASIA': { center: [100, 35], zoom: 2 },
  'SOUTH AMERICA': { center: [-60, -15], zoom: 2.5 },
  'NORTH AMERICA': { center: [-100, 45], zoom: 2 },
  'AFRICA': { center: [20, 0], zoom: 2 },
  'OCEANIA': { center: [140, -25], zoom: 2.5 },
};

// UN M49 numeric codes used by world-atlas
const NUMERIC_TO_COUNTRY: Record<string, string> = {
  '191': 'Croatia',
  '372': 'Ireland',
  '826': 'United Kingdom',
  '170': 'Colombia',
  '840': 'United States',
  '528': 'The Netherlands',
  '152': 'Chile',
  '032': 'Argentina',
  '724': 'Spain',
  '250': 'France',
  '380': 'Italy',
  '276': 'Germany',
  '620': 'Portugal',
  '300': 'Greece',
  '392': 'Japan',
  '036': 'Australia',
  '554': 'New Zealand',
  '076': 'Brazil',
  '604': 'Peru',
  '068': 'Bolivia',
  '484': 'Mexico',
  '124': 'Canada',
  '352': 'Iceland',
  '578': 'Norway',
  '752': 'Sweden',
  '208': 'Denmark',
  '246': 'Finland',
  '616': 'Poland',
  '203': 'Czech Republic',
  '040': 'Austria',
  '756': 'Switzerland',
  '056': 'Belgium',
  '348': 'Hungary',
  '642': 'Romania',
  '792': 'Turkey',
  '818': 'Egypt',
  '504': 'Morocco',
  '710': 'South Africa',
  '404': 'Kenya',
  '834': 'Tanzania',
  '764': 'Thailand',
  '704': 'Vietnam',
  '360': 'Indonesia',
  '458': 'Malaysia',
  '702': 'Singapore',
  '608': 'Philippines',
  '410': 'South Korea',
  '156': 'China',
  '356': 'India',
  '524': 'Nepal',
  '144': 'Sri Lanka',
  '784': 'UAE',
  '376': 'Israel',
  '400': 'Jordan',
  '218': 'Ecuador',
};

interface CountryData {
  name: string;
  tripCount: number;
  trips: Array<{
    title: string;
    tripId: string;
  }>;
}

interface WorldMapProps {
  countriesWithTrips: Record<string, CountryData>;
  basePath?: string; // '/es' for Spanish, '' for English
}

export default function WorldMap({ countriesWithTrips, basePath = '' }: WorldMapProps) {
  const [tooltipContent, setTooltipContent] = useState<string>('');
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [activeContinent, setActiveContinent] = useState<string>('WORLD');
  
  const currentView = CONTINENT_VIEWS[activeContinent];

  // Build a set of numeric IDs that have trips
  const visitedNumericIDs = useMemo(() => {
    const ids = new Set<string>();
    
    // Create reverse lookup: country name -> numeric ID
    const countryToNumeric: Record<string, string> = {};
    Object.entries(NUMERIC_TO_COUNTRY).forEach(([numId, name]) => {
      countryToNumeric[name] = numId;
      // Handle variations
      if (name === 'The Netherlands') countryToNumeric['Netherlands'] = numId;
      if (name === 'United States') countryToNumeric['USA'] = numId;
      if (name === 'United Kingdom') countryToNumeric['UK'] = numId;
    });
    
    Object.keys(countriesWithTrips).forEach(countryName => {
      const numericId = countryToNumeric[countryName];
      if (numericId) {
        ids.add(numericId);
      }
    });
    
    return ids;
  }, [countriesWithTrips]);

  const handleCountryClick = (geo: any) => {
    const numericId = geo.id;
    const countryName = NUMERIC_TO_COUNTRY[numericId];
    
    if (!countryName) return;
    
    // Find the country data (handle name variations)
    const countryData = countriesWithTrips[countryName] || 
                        countriesWithTrips['Netherlands'] || // fallback for "The Netherlands"
                        null;
    
    // Try to find by checking all entries
    const matchedEntry = Object.entries(countriesWithTrips).find(([name]) => {
      const nameNumericId = Object.entries(NUMERIC_TO_COUNTRY)
        .find(([, n]) => n === name || 
              (n === 'The Netherlands' && name === 'Netherlands') ||
              (n === 'United States' && name === 'USA'))?.[0];
      return nameNumericId === numericId;
    });
    
    if (matchedEntry) {
      const [name, data] = matchedEntry;
      if (data.tripCount === 1) {
        window.location.href = `${basePath}/trip/${data.trips[0].tripId}`;
      } else {
        window.location.href = `${basePath}/country/${encodeURIComponent(name.toLowerCase().replace(/\s+/g, '-'))}`;
      }
    }
  };

  const handleMouseEnter = (geo: any, event: React.MouseEvent) => {
    const numericId = geo.id;
    const countryName = NUMERIC_TO_COUNTRY[numericId] || geo.properties?.name || 'Unknown';
    
    // Check if visited
    const isVisited = visitedNumericIDs.has(numericId);
    
    if (isVisited) {
      // Find trip count
      const matchedEntry = Object.entries(countriesWithTrips).find(([name]) => {
        const nameNumericId = Object.entries(NUMERIC_TO_COUNTRY)
          .find(([, n]) => n === name || 
                (n === 'The Netherlands' && name === 'Netherlands'))?.[0];
        return nameNumericId === numericId;
      });
      
      if (matchedEntry) {
        const [, data] = matchedEntry;
        setTooltipContent(`${countryName}: ${data.tripCount} trip${data.tripCount > 1 ? 's' : ''}`);
      } else {
        setTooltipContent(countryName);
      }
    } else {
      setTooltipContent(countryName);
    }
    
    setTooltipPosition({ x: event.clientX, y: event.clientY });
  };

  const handleMouseLeave = () => {
    setTooltipContent('');
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (tooltipContent) {
      setTooltipPosition({ x: event.clientX, y: event.clientY });
    }
  };

  return (
    <div className="world-map-wrapper">
      {/* Continent Controls */}
      <div className="continent-controls">
        {Object.keys(CONTINENT_VIEWS).map((continent) => (
          <button
            key={continent}
            className={`continent-btn ${activeContinent === continent ? 'active' : ''}`}
            onClick={() => setActiveContinent(continent)}
          >
            {continent}
          </button>
        ))}
      </div>
      
      <div className="world-map-container" onMouseMove={handleMouseMove}>
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{
            scale: 120,
            center: [0, 20],
          }}
          style={{
            width: '100%',
            height: 'auto',
          }}
        >
          <ZoomableGroup
            center={currentView.center}
            zoom={currentView.zoom}
          >
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const isVisited = visitedNumericIDs.has(geo.id);
                  
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      onMouseEnter={(event) => handleMouseEnter(geo, event)}
                      onMouseLeave={handleMouseLeave}
                      onClick={() => isVisited && handleCountryClick(geo)}
                      style={{
                        default: {
                          fill: isVisited ? '#c5a47e' : '#e8e8e0',
                          stroke: '#ffffff',
                          strokeWidth: 0.5,
                          outline: 'none',
                          cursor: isVisited ? 'pointer' : 'default',
                        },
                        hover: {
                          fill: isVisited ? '#a08060' : '#d5d5cd',
                          stroke: '#ffffff',
                          strokeWidth: 0.5,
                          outline: 'none',
                          cursor: isVisited ? 'pointer' : 'default',
                        },
                        pressed: {
                          fill: isVisited ? '#8a6a4a' : '#c5c5bd',
                          stroke: '#ffffff',
                          strokeWidth: 0.5,
                          outline: 'none',
                        },
                      }}
                    />
                  );
                })
              }
            </Geographies>
          </ZoomableGroup>
        </ComposableMap>
        
        {tooltipContent && (
          <div
            className="map-tooltip"
            style={{
              position: 'fixed',
              left: tooltipPosition.x + 10,
              top: tooltipPosition.y - 30,
              backgroundColor: '#2d2d2d',
              color: '#ffffff',
              padding: '6px 12px',
              borderRadius: '4px',
              fontSize: '13px',
              fontFamily: 'Montserrat, sans-serif',
              pointerEvents: 'none',
              zIndex: 1000,
              whiteSpace: 'nowrap',
            }}
          >
            {tooltipContent}
          </div>
        )}
      </div>
      
      <style>{`
        .world-map-wrapper {
          position: relative;
        }
        
        .continent-controls {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 1rem;
          justify-content: center;
        }
        
        .continent-btn {
          font-family: 'Montserrat', sans-serif;
          font-size: 0.7rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          padding: 0.4rem 0.8rem;
          border: 1px solid #e5e5e5;
          background: #ffffff;
          color: #666666;
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        
        .continent-btn:hover {
          border-color: #c5a47e;
          color: #2d2d2d;
        }
        
        .continent-btn.active {
          background: #c5a47e;
          border-color: #c5a47e;
          color: #ffffff;
        }
        
        .world-map-container {
          background: linear-gradient(180deg, #f8f8f5 0%, #f0f0eb 100%);
          border-radius: 8px;
          padding: 1rem;
          box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.04);
        }
        
        .world-map-container svg {
          display: block;
        }
      `}</style>
    </div>
  );
}

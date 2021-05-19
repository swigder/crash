let metadata = {}
$.ajax({
    url: "data/file-metadata.json",
    async: false,
    dataType: "json",
    success: data => {
        metadata = data;
        metadata.filenames = new Set(metadata.filenames)
        window.dispatchEvent(new CustomEvent("metadata-load", {
            detail: metadata
        }))
    }
})

// TODO: Check that retina display tiles do not cause problems on non-retina devices (`@2x` below).
mapboxgl.accessToken = 'pk.eyJ1Ijoic3dpZ2RlciIsImEiOiJja29hbnI2bmQwMm0zMm91aHhlNHlhOHF2In0.FaLm4CYTTue7x4-NWm8p5g';
let map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/golmschenk/ckoss0cw40zbg17pen2nl0zv3',
    center: [-76.88, 39.00],
    zoom: 13,
    maxZoom: 18,
});

map.addControl(
    new MapboxGeocoder({
        accessToken: mapboxgl.accessToken,
        mapboxgl: mapboxgl,
        flyTo: {
            duration: 0,
        },
    })
);

map.on('load', getNewData);
map.on('moveend', getNewData);
map.on('zoomend', getNewData);
map.on('sourcedata', updateCount);

function onMarkerClick(e) {
    $("#crash-tab").click()
    let detail = e.features[0].properties
    detail.injuries = JSON.parse(detail.injuries)  // TODO: figure out why this is turning into a string.
    window.dispatchEvent(new CustomEvent("items-load", {
        detail: e.features[0].properties
    }));
}

function roundLatLongDown(latlong) {
    let interval = metadata.latlong_interval
    return Math.floor(latlong / interval) * interval;
}

function roundLatLongUp(latlong) {
    let interval = metadata.latlong_interval
    return Math.ceil(latlong / interval) * interval + interval;
}

let loadedFiles = new Set()

function getNewData() {
    let bounds = map.getBounds()
    let south = roundLatLongDown(bounds.getSouth())
    let north = roundLatLongUp(bounds.getNorth())
    let west = roundLatLongDown(bounds.getWest())
    let east = roundLatLongUp(bounds.getEast())
    for (let lat = south; lat < north; lat += metadata.latlong_interval) {
        for (let long = west; long < east; long += metadata.latlong_interval) {
            let filename = `data/data-${lat}_${long}.json`
            if (map.getSource(filename) || !metadata.filenames.has(filename)) {
                continue;
            }
            loadedFiles.add(filename)
            map.addSource(filename, {
                'type': 'geojson',
                'data': filename,
                'cluster': false,
            });
            map.addLayer({
                id: filename,
                type: 'circle',
                source: filename,
                'paint': {
                    'circle-color': [
                        'match',
                        ['get', 'harm'],
                        'bike',
                        '#fbb03b',
                        'car',
                        '#223b53',
                        'ped',
                        '#e55e5e',
                        /* other */
                        '#3bb2d0',
                    ],
                    'circle-radius': {
                        stops: [[4, 1], [7, 3], [10, 6], [13, 10], [16, 20]]
                    }
                },
            });
            map.on('click', filename, onMarkerClick);
        }
    }
    updateCount()
}

function getCounts() {
    let crash_count = 0
    let fatality_count = 0
    let features = map.queryRenderedFeatures({layers: Array.from(loadedFiles)});
    features.forEach(function (f) {
        crash_count++
        fatality_count += f.properties.num_fatalities
    });
    return {crash_count: crash_count, fatality_count: fatality_count};
}

function updateCount() {
    window.dispatchEvent(new CustomEvent("count-updated", {
        detail: getCounts()
    }));
}

const filters = {
    "harm": new Set(["ped", "car", "bike", "other"])
}

function showFeature(marker) {
    return marker.options.data && filters["harm"].has(marker.options.data.harm)
}

$("button").on('click', (event) => {
    let button = $(event.currentTarget)
    button.toggleClass('is-dark is-light is-selected');
    let filter = button.attr("data-filter-type")
    let value = button.attr("data-filter-value")
    if (button.hasClass('is-selected')) {
        filters[filter].add(value);
    } else {
        filters[filter].delete(value);
    }
    // clusterLayer.clearLayers()
    // clusterLayer.addLayers(allMarkers.filter(showFeature))
    updateCount()
});

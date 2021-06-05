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
    minZoom: 2,
    maxZoom: 18,
});

map.addControl(
    new MapboxGeocoder({
        accessToken: mapboxgl.accessToken,
        mapboxgl: mapboxgl,
        flyTo: {
            duration: 0,
        },
        placeholder: 'Jump to location',
        countries: 'US',
        marker: false,
    })
);
map.addControl(
    new mapboxgl.ScaleControl({
        unit: 'imperial',
    })
);
map.dragRotate.disable();
map.touchZoomRotate.disableRotation();

let updateCount = debounce(function () {
    window.dispatchEvent(new CustomEvent("count-updated", {
        detail: getCounts()
    }));
}, 250)
let mapChanged = debounce(function () {
    updateCount();
    getNewData();
    if (clickedLocation && (!map.getBounds().contains(clickedLocation) || map.getZoom() < 10)) {
        clickedLocation = null
        $("#map-tab").click();
    }
}, 250)

map.on('load', getNewData);
map.on('moveend', mapChanged);
map.on('zoomend', mapChanged);
map.on('sourcedata', updateCount);

let fullData = new Map()
let clickedLocation = null

function onMarkerClick(e) {
    clickedLocation = e.lngLat
    let properties = new Map(Object.entries(e.features[0].properties))
    if (fullData.has(properties.get("id"))) {
        dispatchDetails(properties)
    } else {
        let url = `data/data-${roundLatLongDown(e.lngLat.lat)}_${roundLatLongDown(e.lngLat.lng)}-full.json`
        $.ajax({
            url: url,
            properties: properties,
            success: function (data) {
                mergeMaps(fullData, data)
                dispatchDetails(this.properties);
            }
        });
    }
}

let currentHover = null

function onMarkerHover(e) {
    map.getCanvas().style.cursor = 'pointer';

    let newHover = {
        id: e.features[0].id,
        source: e.features[0].layer.source,
    }

    if (!currentHover || currentHover.id !== newHover.id || currentHover.source !== newHover.source) {
        if (currentHover) {
            map.setFeatureState(currentHover, {hover: false});
        }
        currentHover = newHover;
        map.setFeatureState(newHover, {hover: true});
    }
}

function onMarkerUnhover(e) {
    map.getCanvas().style.cursor = '';

    if (currentHover) {
        map.setFeatureState(currentHover, {hover: false});
    }
    currentHover = null;
}

function dispatchDetails(properties) {
    mergeMaps(properties, fullData.get(properties.get("id")))
    let url_params = properties.get('id').split('-')
    properties.set('url', `https://crashviewer.nhtsa.dot.gov/CrashAPI/crashes/GetCaseDetails?stateCase=${url_params[2]}&caseYear=${url_params[0]}&state=${url_params[1]}&format=xml`)
    window.dispatchEvent(new CustomEvent("items-load", {
        detail: Object.fromEntries(properties),
    }));
    $("#crash-tab").click()
}

function roundLatLongDown(latlong) {
    let interval = metadata.latlong_interval
    return Math.floor(latlong / interval) * interval;
}

function roundLatLongUp(latlong) {
    let interval = metadata.latlong_interval
    return Math.ceil(latlong / interval) * interval;
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
                'generateId': true,
            });
            map.addLayer({
                id: filename,
                type: 'circle',
                source: filename,
                'paint': {
                    'circle-opacity': .8,
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
                        stops: [[4, 1], [10, 3], [13, 6], [16, 8]]
                    },
                    'circle-stroke-width': [
                        'case',
                        ['boolean', ['feature-state', 'hover'], false,],
                        2,
                        0,
                    ],
                    'circle-stroke-color': [
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
                },
            });
            map.on('click', filename, onMarkerClick);
            map.on('mousemove', filename, onMarkerHover);
            map.on('mouseleave', filename, onMarkerUnhover);
            setFilter(filename);
        }
    }
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

const filters = {
    "harm": new Set(["ped", "car", "bike", "other"])
}

function setFilter(layer) {
    map.setFilter(layer, ['in', ['get', 'harm'], ['literal', Array.from(filters["harm"])]]);
}

$("button").on('click', (event) => {
    let button = $(event.currentTarget)
    button.toggleClass('is-selected');
    let filter = button.attr("data-filter-type")
    let value = button.attr("data-filter-value")
    if (button.hasClass('is-selected')) {
        filters[filter].add(value);
    } else {
        filters[filter].delete(value);
    }
    loadedFiles.forEach(function (f) {
        setFilter(f)
    });
    updateCount()
});

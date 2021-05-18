const markerSize = 20

const emojis = {
    'car': '🚙',
    'bike': '🚴',
    'ped': '🚶',
    'other': ''
}

const loaded = new Set()

let metadata = {}
$.ajax({
    url: "data/file-metadata.json",
    async: false,
    dataType: "json",
    success: data => {
        metadata = data;
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

map.on('load', getNewData);
map.on('moveend', getNewData);
map.on('zoomend', getNewData);

function onMarkerClick(e) {
    $("#crash-tab").click()
    window.dispatchEvent(new CustomEvent("items-load", {
        detail: e.layer.options.data
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

function getNewData() {
    let bounds = map.getBounds()
    let south = roundLatLongDown(bounds.getSouth())
    let north = roundLatLongUp(bounds.getNorth())
    let west = roundLatLongDown(bounds.getWest())
    let east = roundLatLongUp(bounds.getEast())
    for (let lat = south; lat < north; lat += metadata.latlong_interval) {
        for (let long = west; long < east; long += metadata.latlong_interval) {
            let filename = `data/data-${lat}_${long}.json`
            if (map.getSource(filename)) {
                continue;
            }
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
                        'other',
                        '#3bb2d0',
                        /* other */ '#ccc'
                    ],
                    'circle-radius': {
                        stops: [[4, 1], [7, 3], [10, 6], [13, 10], [16, 20]]
                    }
                },
            });
            // updateCount();
        }
    }
}

function getCounts() {
    let crash_count = 0
    let fatality_count = 0
    allMarkers.filter(marker => map.getBounds().contains(marker.getLatLng()) && showFeature(marker)).forEach(function (marker) {
        crash_count++
        fatality_count += marker.options.data.num_fatalities
    })
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

$('#location-input').on('keydown', function (event) {
    if (event.key === "Enter") {
        $.getJSON(`https://api.mapbox.com/geocoding/v5/mapbox.places/${event.target.value}.json`, {
            access_token: 'pk.eyJ1Ijoic3dpZ2RlciIsImEiOiJja29hbnI2bmQwMm0zMm91aHhlNHlhOHF2In0.FaLm4CYTTue7x4-NWm8p5g',
            limit: 1
        }, function (data) {
            let result = data.features[0]
            let longLat = result.center
            map.setView([longLat[1], longLat[0]], 13);
            event.target.value = result.place_name
        })
    }
});

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
    clusterLayer.clearLayers()
    clusterLayer.addLayers(allMarkers.filter(showFeature))
    updateCount()
});

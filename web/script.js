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

let allMarkers = []

let map = L.map('map')
map.on('moveend zoomend load', getNewData);

// TODO: Check that retina display tiles do not cause problems on non-retina devices (`@2x` below).
L.tileLayer('https://api.mapbox.com/styles/v1/{styleAuthor}/{styleId}/tiles/{z}/{x}/{y}@2x?access_token={accessToken}', {
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
    maxZoom: 18,
    styleAuthor: 'golmschenk',
    styleId: 'ckoss0cw40zbg17pen2nl0zv3',
    tileSize: 512,
    zoomOffset: -1,
    accessToken: 'pk.eyJ1Ijoic3dpZ2RlciIsImEiOiJja29hbnI2bmQwMm0zMm91aHhlNHlhOHF2In0.FaLm4CYTTue7x4-NWm8p5g'
}).addTo(map);

function onMarkerClick(e) {
    window.dispatchEvent(new CustomEvent("items-load", {
        detail: e.layer.options.data
    }));
}

function pointToLayer(point) {
    let harm = point.data.harm
    return L.marker(point.latlng, {
        icon: L.divIcon({
            iconSize: [markerSize, markerSize],
            className: `circle ${harm}`,
            html: `${emojis[harm]}️`,
        }),
        data: point.data,
    });
}

let clusterLayer = L.markerClusterGroup({
    spiderfyOnMaxZoom: false,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: false,
    disableClusteringAtZoom: 12,
    chunkedLoading: true,
});
map.addLayer(clusterLayer)

map.setView([39.00, -76.88], 13)

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
    let tasks = []
    for (let lat = south; lat < north; lat += metadata.latlong_interval) {
        for (let long = west; long < east; long += metadata.latlong_interval) {
            let file = `data/data-${lat}_${long}.json`
            if (!loaded.has(file)) {
                loaded.add(file)
                tasks.push($.Deferred(function (defer) {
                    $.ajax(file).then(defer.resolve, defer.resolve);
                }).promise())
            }
        }
    }
    $.when(...tasks).then(function (...allData) {
        allData.forEach(data => {
            if (data[1] === "success") {
                Array.prototype.push.apply(allMarkers, data[0].map(d => pointToLayer(d)))
            }
        })
        if (tasks.length > 0) {
            clusterLayer.clearLayers()
            clusterLayer.addLayers(L.featureGroup(allMarkers).on('click', onMarkerClick))
        }
        updateCount();
    });
}

function getCounts() {
    let crash_count = 0
    let fatality_count = 0
    allMarkers.forEach(function (marker) {

    })
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

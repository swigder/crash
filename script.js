let map = L.map('map').setView([39.00, -76.88], 13);

L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}', {
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
    maxZoom: 18,
    id: 'mapbox/streets-v11',
    tileSize: 512,
    zoomOffset: -1,
    accessToken: 'pk.eyJ1Ijoic3dpZ2RlciIsImEiOiJja29hbnI2bmQwMm0zMm91aHhlNHlhOHF2In0.FaLm4CYTTue7x4-NWm8p5g'
}).addTo(map);

const emojis = {
    'car': '🚙',
    'bike': '🚴',
    'ped': '🚶',
    'other': ''
}

$.getJSON('geojson.json', function (data) {
    L.geoJSON(data, {
        style: function (feature) {
            return feature.properties && feature.properties.style;
        },

        onEachFeature: function (feature, layer) {
            // layer.bindPopup(feature.properties.year);
            layer.on('click', function (e) {
                window.dispatchEvent(new CustomEvent("items-load", {
                    detail: e.sourceTarget.feature.properties
                }));
            })
        },

        pointToLayer: function (feature, latlng) {
            const size = 20
            let harm = feature.properties.harm
            return L.marker(latlng, {
                icon: L.divIcon({
                    iconSize: [size, size],
                    // iconAnchor: [size / 2, size + 9],
                    className: `circle ${harm}`,
                    html: `${emojis[harm]}️`,
                })
            });
        }
    }).addTo(map);
});

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 18:03:29 2026

@author: airamsarmiento
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
script_auto.py
Descarga automáticamente datos de Copernicus (thetao y corrientes),
recorta la región de Canarias, genera la figura SST + Surface Currents
y guarda latest.png listo para la web.
"""
import os
import copernicusmarine
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.ticker import MaxNLocator
import xarray as xr
import pandas as pd
from datetime import datetime

from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg

today = datetime.utcnow().strftime("%Y-%m-%d")

img = mpimg.imread("figures/buoy.png")

# -----------------------------
# Login Copernicus
# -----------------------------
copernicusmarine.login(
    username=os.environ.get("COPERNICUS_USERNAME"),
    password=os.environ.get("COPERNICUS_PASSWORD")
)


# Leer archivo
df = pd.read_excel("data/coordenadas.xlsx")

# Separar categorías
ctd = df[df["Category"] == "CTD"]
bio = df[df["Category"] == "BIO"]



# -----------------------------
# 2️⃣ SST + Corrientes superficiales
# -----------------------------
ds_sst = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
    variables=["thetao"],
    minimum_longitude=-23,
    maximum_longitude=-5,
    minimum_latitude=20,
    maximum_latitude=40,
    start_datetime=today,
    end_datetime=today
)

ds_cur = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
    variables=["uo","vo"],
    minimum_longitude=-23,
    maximum_longitude=-5,
    minimum_latitude=20,
    maximum_latitude=40,
    start_datetime=today,
    end_datetime=today
)

sst = ds_sst["thetao"].isel(time=0, depth=0)
uo  = ds_cur["uo"].isel(time=0, depth=0)
vo  = ds_cur["vo"].isel(time=0, depth=0)
lons = ds_sst["longitude"].values
lats = ds_sst["latitude"].values
lon2d, lat2d = np.meshgrid(lons, lats)
date_str = str(np.datetime_as_string(ds_sst.time.values[0], unit='D'))


# -----------------------------
# Guardar figura
# -----------------------------
out_path = "figures"
os.makedirs(out_path, exist_ok=True)


# -----------------------------
# 3️⃣ SST + flujo geostrófico
# -----------------------------
ds_SSH = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_phy-ssh_anfc_detided-0.027deg_P1D-m",
    variables=["zos_detided"],
    minimum_longitude=-23,
    maximum_longitude=-5,
    minimum_latitude=20,
    maximum_latitude=40,
    start_datetime=today,
    end_datetime=today
)
ssh = ds_SSH["zos_detided"].isel(time=0).values

# Calcular flujo geostrófico
lons = ds_SSH["longitude"].values
lats = ds_SSH["latitude"].values
lon2d, lat2d = np.meshgrid(lons, lats)
phi = np.deg2rad(lat2d)
f = 2*7.2921e-5*np.sin(phi)
dlat = np.deg2rad(lats[1]-lats[0])
dlon = np.deg2rad(lons[1]-lons[0])
dy = 6371000*dlat
dx = 6371000*np.cos(phi)*dlon
dssh_dy = np.gradient(ssh, axis=0)/dy
dssh_dx = np.gradient(ssh, axis=1)/dx
ugeo = -9.81/f*dssh_dy
vgeo = 9.81/f*dssh_dx

fig = plt.figure(figsize=(8,6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([-19, -5, 26.5, 40], crs=ccrs.PlateCarree())
pcm = ax.pcolormesh(lon2d, lat2d, ds_sst["thetao"].isel(time=0, depth=0).values,
                    cmap='turbo', shading='auto', transform=ccrs.PlateCarree())
step = 10
q = ax.quiver(lon2d[::step,::step], lat2d[::step,::step], ugeo[::step,::step], vgeo[::step,::step],
              scale=1, scale_units='inches', width=0.0025, color='black', transform=ccrs.PlateCarree())
ax.quiverkey(q, 0.88, 0.04, 0.5, "0.5 m/s", labelpos='E', coordinates='axes', fontproperties={'size':10})
ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgrey')
ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1.2)
gl = ax.gridlines(draw_labels=True, linewidth=0)
gl.top_labels = False
gl.right_labels = False
gl.left_labels = True
gl.bottom_labels = True
plt.title(f"SST + Geostrophic Currents – {date_str}")
plt.colorbar(pcm, label="SST [°C]")

# Definir estilos para las categorías
categories = {
    "CTD": {"color": "red", "facecolors": "red", "marker": "o", "s": 60, "edgecolor": "black"},
    "BIO": {"color": "green", "facecolors": "none", "marker": "D", "s": 80, "linewidth": 2}
}

# Dibujar todas las estaciones
for cat, style in categories.items():
    df_cat = df[df["Category"] == cat]
    ax.scatter(
        df_cat["Longitude"], df_cat["Latitude"],
        transform=ccrs.PlateCarree(),
        label=f"{cat} stations",
        **style
    )

ax.legend(loc="upper right", fontsize=10, frameon=True)

# Coordenadas de la boya y de la primera estación
lon_estoc, lat_estoc = -16.3, 30.5
lon_station1, lat_station1 = -15.5, 29.167

# Insertar imagen de la boya
ab = AnnotationBbox(
    OffsetImage(img, zoom=0.04),
    (lon_estoc, lat_estoc),
    frameon=False,
    transform=ccrs.PlateCarree(),
    zorder=15
)
ax.add_artist(ab)

# Flecha hacia la estación 1
ax.annotate(
    "",
    xy=(lon_station1, lat_station1),
    xytext=(lon_estoc, lat_estoc),
    arrowprops=dict(arrowstyle="->", color="black", linewidth=1.5),
    transform=ccrs.PlateCarree(),
    zorder=10
)
plt.tight_layout()


# -----------------------------
# Guardar figura
# -----------------------------

SSTgeo_path = os.path.join(out_path, "SSTgeo.png")
fig.savefig(SSTgeo_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como SSTgeo.png")




# -----------------------------
# 4️⃣ CHL + flujo geostrófico
# -----------------------------
ds_CHL = copernicusmarine.open_dataset(
    dataset_id="cmems_obs-oc_atl_bgc-plankton_my_l4-gapfree-multi-1km_P1D",
    variables=["CHL"],
    minimum_longitude=-19,
    maximum_longitude=-5,
    minimum_latitude=26.5,
    maximum_latitude=40,
    start_datetime="2026-02-16",
    end_datetime=today
)
time_chl = pd.to_datetime(ds_CHL.time.values)
last_date_chl = time_chl.max()
ds_CHL_day = ds_CHL.sel(time=last_date_chl)
lons_chl = ds_CHL_day["longitude"].values
lats_chl = ds_CHL_day["latitude"].values
lon2d_chl, lat2d_chl = np.meshgrid(lons_chl, lats_chl)

chl = ds_CHL_day["CHL"].values

## Crear figura
fig = plt.figure(figsize=(8,6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([lons_chl.min(), lons_chl.max(), lats_chl.min(), lats_chl.max()], crs=ccrs.PlateCarree())

# Colormesh de CHL usando paleta de SST ('turbo')
# Definir rango de colores según percentiles para no ser afectado por valores extremos
vmin = np.nanpercentile(chl, 5)    # valor por debajo del 5% se pone al mínimo color
vmax = np.nanpercentile(chl, 95)  # valor por encima del 95% se pone al máximo color

pcm = ax.pcolormesh(
    lon2d_chl, lat2d_chl, chl,
    cmap='jet', shading='auto',
    vmin=vmin, vmax=vmax,  # aquí ajustas la paleta
    transform=ccrs.PlateCarree()
)

# Interpolar flujo geostrófico a la malla de CHL
import xarray as xr

ugeo_da = xr.DataArray(ugeo, coords=[ds_sst.latitude, ds_sst.longitude], dims=["latitude", "longitude"])
vgeo_da = xr.DataArray(vgeo, coords=[ds_sst.latitude, ds_sst.longitude], dims=["latitude", "longitude"])

ugeo_interp = ugeo_da.interp(latitude=lats_chl, longitude=lons_chl)
vgeo_interp = vgeo_da.interp(latitude=lats_chl, longitude=lons_chl)

# Añadir costa y tierra
ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgrey')
ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1.2)

# Gridlines: solo izquierda y abajo
gl = ax.gridlines(draw_labels=True, linewidth=0)
gl.top_labels = False
gl.right_labels = False
gl.left_labels = True
gl.bottom_labels = True

# Título
ax.set_title(f"Chlorophyll – a {last_date_chl.strftime('%Y-%m-%d')}")

# Colorbar
cbar = plt.colorbar(pcm, label="Chlorophyll [mg/m³]")

# Definir estilos para las categorías
categories = {
    "CTD": {"color": "red", "facecolors": "red", "marker": "o", "s": 60, "edgecolor": "black"},
    "BIO": {"color": "green", "facecolors": "none", "marker": "D", "s": 80, "linewidth": 2}
}

# Dibujar todas las estaciones
for cat, style in categories.items():
    df_cat = df[df["Category"] == cat]
    ax.scatter(
        df_cat["Longitude"], df_cat["Latitude"],
        transform=ccrs.PlateCarree(),
        label=f"{cat} stations",
        **style
    )

ax.legend(loc="upper right", fontsize=10, frameon=True)

# Coordenadas de la boya y de la primera estación
lon_estoc, lat_estoc = -16.3, 30.5
lon_station1, lat_station1 = -15.5, 29.167

# Insertar imagen de la boya
ab = AnnotationBbox(
    OffsetImage(img, zoom=0.04),
    (lon_estoc, lat_estoc),
    frameon=False,
    transform=ccrs.PlateCarree(),
    zorder=15
)
ax.add_artist(ab)

# Flecha hacia la estación 1
ax.annotate(
    "",
    xy=(lon_station1, lat_station1),
    xytext=(lon_estoc, lat_estoc),
    arrowprops=dict(arrowstyle="->", color="black", linewidth=1.5),
    transform=ccrs.PlateCarree(),
    zorder=10
)

plt.tight_layout()



# -----------------------------
# Guardar figura
# -----------------------------

CHLgeo_path = os.path.join(out_path, "CHLgeo.png")
fig.savefig(CHLgeo_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como CHLgeo.png")




#### SSH

# -----------------------------
# SSH dataset
# -----------------------------
ds_SSH = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_phy-ssh_anfc_detided-0.027deg_P1D-m",
    variables=["zos_detided"],
    minimum_longitude=-19,
    maximum_longitude=-5,
    minimum_latitude=26.5,
    maximum_latitude=40,
    start_datetime=today,
    end_datetime=today
)

ssh = ds_SSH["zos_detided"].isel(time=0).values
lons_ssh = ds_SSH["longitude"].values
lats_ssh = ds_SSH["latitude"].values
lon2d_ssh, lat2d_ssh = np.meshgrid(lons_ssh, lats_ssh)

# -----------------------------
# Reinterpolar flujo geostrófico si es necesario
# -----------------------------
# ugeo, vgeo vienen del SST o de tu cálculo geostrófico
ugeo_da = xr.DataArray(ugeo, coords=[ds_sst.latitude, ds_sst.longitude], dims=["latitude", "longitude"])
vgeo_da = xr.DataArray(vgeo, coords=[ds_sst.latitude, ds_sst.longitude], dims=["latitude", "longitude"])

ugeo_interp = ugeo_da.interp(latitude=lats_ssh, longitude=lons_ssh)
vgeo_interp = vgeo_da.interp(latitude=lats_ssh, longitude=lons_ssh)

# -----------------------------
# Crear figura
# -----------------------------
fig = plt.figure(figsize=(8,6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([lons_ssh.min(), lons_ssh.max(), lats_ssh.min(), lats_ssh.max()], crs=ccrs.PlateCarree())

# SSH
pcm = ax.pcolormesh(
    lon2d_ssh, lat2d_ssh, ssh,
    cmap='RdYlBu_r', shading='auto',
    transform=ccrs.PlateCarree()
)

# Flechas geostróficas
step = 10  # ajustar según densidad de flechas
q = ax.quiver(
    lon2d_ssh[::step, ::step], lat2d_ssh[::step, ::step],
    ugeo_interp.values[::step, ::step], vgeo_interp.values[::step, ::step],
    scale=1, scale_units='inches', width=0.0025,
    color='black', transform=ccrs.PlateCarree()
)

ax.quiverkey(q, 0.88, 0.04, 0.5, "0.5 m/s", labelpos='E', coordinates='axes', fontproperties={'size':10})

# Tierra y costa
ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgrey')
ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1.2)

# Gridlines (solo etiquetas izquierda y abajo)
gl = ax.gridlines(draw_labels=True, linewidth=0)
gl.top_labels = False
gl.right_labels = False
gl.left_labels = True
gl.bottom_labels = True

# Título y colorbar
date_str = str(np.datetime_as_string(ds_SSH.time.values[0], unit='D'))
ax.set_title(f"SSH + Geostrophic Flow – {date_str}", fontsize=14)

cbar = plt.colorbar(pcm, orientation='vertical', pad=0.02, aspect=25)
cbar.set_label("Sea Surface Height [m]", fontsize=12)

# Definir estilos para las categorías
categories = {
    "CTD": {"color": "red", "facecolors": "red", "marker": "o", "s": 60, "edgecolor": "black"},
    "BIO": {"color": "green", "facecolors": "none", "marker": "D", "s": 80, "linewidth": 2}
}

# Dibujar todas las estaciones
for cat, style in categories.items():
    df_cat = df[df["Category"] == cat]
    ax.scatter(
        df_cat["Longitude"], df_cat["Latitude"],
        transform=ccrs.PlateCarree(),
        label=f"{cat} stations",
        **style
    )

ax.legend(loc="upper right", fontsize=10, frameon=True)

# Coordenadas de la boya y de la primera estación
lon_estoc, lat_estoc = -16.3, 30.5
lon_station1, lat_station1 = -15.5, 29.167

# Insertar imagen de la boya
ab = AnnotationBbox(
    OffsetImage(img, zoom=0.04),
    (lon_estoc, lat_estoc),
    frameon=False,
    transform=ccrs.PlateCarree(),
    zorder=15
)
ax.add_artist(ab)

# Flecha hacia la estación 1
ax.annotate(
    "",
    xy=(lon_station1, lat_station1),
    xytext=(lon_estoc, lat_estoc),
    arrowprops=dict(arrowstyle="->", color="black", linewidth=1.5),
    transform=ccrs.PlateCarree(),
    zorder=10
)

plt.tight_layout()


# -----------------------------
# Guardar figura
# -----------------------------

SSHgeo_path = os.path.join(out_path, "SSHgeo.png")
fig.savefig(SSHgeo_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como SSHgeo.png")

# -----------------------------
# Guardar figura
# -----------------------------










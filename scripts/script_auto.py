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




####################################################################


##### secciones verticales
from scipy.interpolate import RegularGridInterpolator, interp1d
import numpy as np
import matplotlib.pyplot as plt



# Limitar a 0-6000 m de profundidad
ds_sst = ds_sst.sel(depth=slice(0, 6000))


# Ordenar estaciones por latitud para la sección
df = ctd.sort_values("Latitude")
lons_st = df["Longitude"].values
lats_st = df["Latitude"].values
names_st = df["Station"].values

# --- Extraer perfiles de temperatura a lo largo de la sección ---
# Para simplificar: tomar la columna más cercana a cada estación

###### Temperature

thetao_profiles = ds_sst["thetao"].sel(
    longitude=xr.DataArray(lons_st, dims="station"),
    latitude=xr.DataArray(lats_st, dims="station"),
    method="nearest"
)

depths = ds_sst["depth"].values

T = thetao_profiles.values  # (depth, station) o (time, depth, station)

T = T.squeeze()  # ahora T.shape será (50, 24)
print(T.shape)   # (50, 24)

# Crear interpolador

# --- Interpolador para suavizado ---
interp_func = RegularGridInterpolator(
    (depths, np.arange(len(names_st))),  # (profundidad, estación)
    T,
    method='linear',  # cambiar a 'cubic' si quieres más suavizado
    bounds_error=False,
    fill_value=np.nan
)

# --- Grilla fina ---
x_fine = np.linspace(0, len(names_st)-1, 200)  # subpuntos entre estaciones
z_fine = np.linspace(depths.min(), depths.max(), 200)  # más puntos en profundidad
Z, X = np.meshgrid(z_fine, x_fine, indexing='ij')

# --- Interpolación ---
T_smooth = interp_func(np.array([Z.ravel(), X.ravel()]).T).reshape(Z.shape)


x = np.arange(len(lats_st))  # eje horizontal (transecto)



#####################################
##### Salinidad

# --- Abrir dataset de salinidad (salinity = "so" o "sosaline" según producto) ---
ds_salt = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
    variables=["so"],  # salinidad
    minimum_longitude=-23,
    maximum_longitude=-5,
    minimum_latitude=20,
    maximum_latitude=40,
    start_datetime=today,
    end_datetime=today
)

# Limitar a 0-6000 m de profundidad
ds_salt = ds_salt.sel(depth=slice(0, 6000))

# Ordenar estaciones por latitud para la sección
df = ctd.sort_values("Latitude")
lons_st = df["Longitude"].values
lats_st = df["Latitude"].values
names_st = df["Station"].values

# --- Extraer perfiles de salinidad a lo largo de la sección ---
salt_profiles = ds_salt["so"].sel(
    longitude=xr.DataArray(lons_st, dims="station"),
    latitude=xr.DataArray(lats_st, dims="station"),
    method="nearest"
)

depths = ds_salt["depth"].values

S = salt_profiles.values  # (depth, station) o (time, depth, station)
S = S.squeeze()           # ahora S.shape será (profundidad, estaciones)
print(S.shape)            # por ejemplo (50, 24)

# --- Crear interpolador ---
interp_func_s = RegularGridInterpolator(
    (depths, np.arange(len(names_st))),  # (profundidad, estación)
    S,
    method='linear',                     # 'cubic' para más suavizado
    bounds_error=False,
    fill_value=np.nan
)

# --- Crear grilla fina ---
x_fine = np.linspace(0, len(names_st)-1, 200)     # subpuntos entre estaciones
z_fine = np.linspace(depths.min(), depths.max(), 200)  # más puntos en profundidad
Z, X = np.meshgrid(z_fine, x_fine, indexing='ij')

# --- Interpolación ---
S_smooth = interp_func_s(np.array([Z.ravel(), X.ravel()]).T).reshape(Z.shape)

x = np.arange(len(lats_st))  # eje horizontal (transecto)


##### Oxygen
ds_ox = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_bgc_anfc_0.027deg-3D_P1D-m",  # IBI region, daily
    variables=["o2"],  # variable de oxígeno disuelto
    minimum_longitude=-23,
    maximum_longitude=-5,
    minimum_latitude=20,
    maximum_latitude=40,
    start_datetime=today,
    end_datetime=today
)



# Limitar a 0-6000 m
ds_ox = ds_ox.sel(depth=slice(0, 6000))



ox_profiles = []

for lon, lat in zip(lons_st, lats_st):
    prof = ds_ox["o2"].sel(longitude=lon, latitude=lat, method="nearest")
    # Eliminar dimensiones de tamaño 1 (por ejemplo time)
    prof = prof.squeeze()
    ox_profiles.append(prof.values)

# Convertir a array (profundidad, estaciones)
ox_profiles = np.stack(ox_profiles, axis=-1)  # ahora shape = (n_depth, n_stations)
print("Shape ox_profiles:", ox_profiles.shape)  # debería ser (50, 17)

depths = ds_ox["depth"].values

# ----------------------------------------
# Crear interpolador para suavizado
# ----------------------------------------
interp_func = RegularGridInterpolator(
    (depths, np.arange(len(names_st))),  # ejes: profundidad, estaciones
    ox_profiles,
    method='linear',  # o 'cubic' si quieres más suavizado
    bounds_error=False,
    fill_value=np.nan
)

# ----------------------------------------
# Crear grilla fina
# ----------------------------------------
x_fine = np.linspace(0, len(names_st)-1, 200)       # subpuntos entre estaciones
z_fine = np.linspace(depths.min(), depths.max(), 200)  # más puntos en profundidad
Z, X = np.meshgrid(z_fine, x_fine, indexing='ij')

# ----------------------------------------
# Interpolación sobre la grilla fina
# ----------------------------------------
Ox_smooth = interp_func(np.array([Z.ravel(), X.ravel()]).T).reshape(Z.shape)

print("Shape Ox_smooth:", Ox_smooth.shape)  # (200, 200)

###--------------------



##### clorofila


ds_chl = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_bgc_anfc_0.027deg-3D_P1D-m",  # IBI region, daily
    variables=["chl"],  # variable de oxígeno disuelto
    minimum_longitude=-23,
    maximum_longitude=-5,
    minimum_latitude=20,
    maximum_latitude=40,
    start_datetime=today,
    end_datetime=today
)



# Limitar a 0-6000 m
ds_chl = ds_chl.sel(depth=slice(0, 6000))

CHL_profiles = []
for lon, lat in zip(lons_st, lats_st):
    prof = ds_chl["chl"].sel(longitude=lon, latitude=lat, method="nearest")
    CHL_profiles.append(prof.values)

CHL_profiles = np.array(CHL_profiles)  # shape: (n_stations, n_depth)
depths = ds_chl["depth"].values

CHL = CHL_profiles.squeeze()  # quitar dimensiones extra si las hay
print("Shape CHL:", CHL.shape)

# ------------------------
# 2️⃣ Interpolador para suavizado
# ------------------------
interp_func = RegularGridInterpolator(
    (depths, np.arange(len(names_st))),  # (profundidad, estación)
    CHL.T,  # transponer para que quede (depth, station)
    method='linear',
    bounds_error=False,
    fill_value=np.nan
)

# --- 3️⃣ Grilla fina para suavizar ---
x_fine = np.linspace(0, len(names_st)-1, 200)
z_fine = np.linspace(depths.min(), depths.max(), 200)
Z, X = np.meshgrid(z_fine, x_fine, indexing='ij')

# --- 4️⃣ Interpolación ---
CHL_smooth = interp_func(np.array([Z.ravel(), X.ravel()]).T).reshape(Z.shape)

###--------------------


## bathymetri 

import xarray as xr



# opcion segura

bathy = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_glo_phy_my_0.083deg_static",
    variables=["deptho"],
    minimum_longitude=-20,
    maximum_longitude=-5,
    minimum_latitude=26,
    maximum_latitude=42
)


import numpy as np

# puntos de inicio y fin
lon_start, lat_start = -19.981, 26.487
lon_end, lat_end     = -5.011, 41.947

# número de puntos a muestrear en el transecto
n_points = 30

# crear arrays de coordenadas lineales
lons_transect = np.linspace(lon_start, lon_end, n_points)
lats_transect = np.linspace(lat_start, lat_end, n_points)

bathy_section = []

for lon, lat in zip(lons_transect, lats_transect):
    val = bathy["deptho"].sel(longitude=lon, latitude=lat, method="nearest")
    bathy_section.append(val.values)

bathy_line = np.array(bathy_section)

bathy_line_plot = np.copy(bathy_line)
bathy_line_plot = np.nan_to_num(bathy_line_plot, nan=2000)  # reemplazar nan
bathy_line_plot[bathy_line_plot > 2000] = 2000 


import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

# ----------------------------------
# 1️⃣ Extraer temperatura en transecto
# ----------------------------------
theta_section = []

for lon, lat in zip(lons_transect, lats_transect):
    prof = ds_sst["thetao"].sel(longitude=lon, latitude=lat, method="nearest")
    theta_section.append(prof.values)

theta_section = np.array(theta_section)  # (n_points, n_depth)
depths = ds_sst["depth"].values

# ----------------------------------
# 2️⃣ Preparar grilla para interpolación
# ----------------------------------
x = np.arange(len(lons_transect))  # eje horizontal (transecto)
z = depths

# Malla fina
xi = np.linspace(x.min(), x.max(), 400)
zi = np.linspace(0, 2000, 400)  # límite profundidad (ajusta)
XI, ZI = np.meshgrid(xi, zi)

# ----------------------------------
# 3️⃣ Interpolación (MUCHO mejor que RGI)
# ----------------------------------
X_pts, Z_pts = np.meshgrid(x, z)
points = np.array([X_pts.flatten(), Z_pts.flatten()]).T
values = theta_section.T.flatten()

# Interpolación híbrida
VI_lin = griddata(points, values, (XI, ZI), method="linear")
VI_near = griddata(points, values, (XI, ZI), method="nearest")

VI = VI_lin.copy()
VI[np.isnan(VI)] = VI_near[np.isnan(VI)]

# ----------------------------------
# 4️⃣ Interpolar batimetría al mismo eje
# ----------------------------------
from scipy.interpolate import interp1d

bathy_interp = interp1d(
    np.linspace(0, len(bathy_line)-1, len(bathy_line)),
    bathy_line,
    kind="linear",
    bounds_error=False,
    fill_value="extrapolate"
)

bathy_fine = bathy_interp(xi)

# ----------------------------------
# 5️⃣ Enmascarar debajo del fondo
# ----------------------------------
for i in range(len(xi)):
    VI[ZI[:, i] > bathy_fine[i], i] = np.nan
    
    
    
    
import numpy as np
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import cmocean
import matplotlib.colors as mcolors

# ----------------------------------
# 6️⃣ PLOT ESTILO PAPER
# ----------------------------------

# ----------------------------------
# 6️⃣ PUNTOS DE MUESTREO
# ----------------------------------

# Crear malla de estaciones vs profundidad
X_data, Z_data = np.meshgrid(x, depths)

# Máscara de datos válidos
mask = ~np.isnan(T)




##########################################################bathymetri

import copernicusmarine
bathy = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_glo_phy_my_0.083deg_static",
    variables=["deptho"],
    minimum_longitude=-20,
    maximum_longitude=-5,
    minimum_latitude=26,
    maximum_latitude=42
)



# Tomamos las posiciones reales de las estaciones y la batimetría
station_lons = df.groupby("Station")["Longitude"].mean().values
station_lats = df.groupby("Station")["Latitude"].mean().values


lons_click = np.array(station_lons)
lats_click = np.array(station_lats)

# Número de puntos interpolados entre cada par de clics
n_interp = 200  

# Generar arrays finales
lons_transect = []
lats_transect = []

for i in range(len(lons_click)-1):
    lons_segment = np.linspace(lons_click[i], lons_click[i+1], n_interp, endpoint=False)
    lats_segment = np.linspace(lats_click[i], lats_click[i+1], n_interp, endpoint=False)
    lons_transect.extend(lons_segment)
    lats_transect.extend(lats_segment)

# Añadir el último punto
lons_transect.append(lons_click[-1])
lats_transect.append(lats_click[-1])

lons_transect = np.array(lons_transect)
lats_transect = np.array(lats_transect)

# -----------------------------
# 4️⃣ Interpolar batimetría
# -----------------------------
bathy_line = bathy.interp(
    longitude=("points", lons_transect),
    latitude=("points", lats_transect),
    method="linear"
)['deptho'].values


print("Transecto generado con", len(bathy_line), "puntos de batimetría")



###################################### guardamos lo que hemos creado
import xarray as xr
import numpy as np


ds_transect = xr.Dataset(
    {
        "elevation": (("point"), bathy_line)
    },
    coords={
        "longitude": (("point"), lons_transect),
        "latitude": (("point"), lats_transect)
    }
)

# Revisar
print(ds_transect)


# Crear figura
fig, ax = plt.subplots(figsize=(12, 6))

# Graficar línea de batimetría
ax.plot(lats_transect, bathy_line, '-o', color='blue', markersize=4, linewidth=2, label='Batimetría')

# Etiquetas y título
ax.set_xlabel("Longitude (°E)", fontsize=14)
ax.set_ylabel("Depth (m)", fontsize=14)
ax.set_title("Transecto de Batimetría desde GEBCO", fontsize=16)
ax.invert_yaxis()  # profundidad positiva hacia abajo
ax.grid(True)
ax.legend()

plt.show()






from scipy.interpolate import interp1d
import numpy as np

# X[0, :] es el eje horizontal de tu sección
xi = X[0, :]  # eje horizontal de la sección

# Interpolamos la batimetría (bathy_line) a los puntos de X
f_bathy = interp1d(np.linspace(0, 16, len(bathy_line)), bathy_line, kind='linear')
bathy_line_plot = f_bathy(xi)



###############################################


T_ext = T_smooth.copy()
Z_max = 6000

# Extrapolar cada columna
for i in range(T_ext.shape[1]):
    col = T_ext[:, i]
    # Encuentra el último índice no NaN
    valid_idx = np.where(~np.isnan(col))[0]
    if len(valid_idx) == 0:
        continue  # toda la columna es NaN
    last_valid = valid_idx[-1]
    # Extender el último valor válido hasta el final de la columna
    col[last_valid:] = col[last_valid]
    T_ext[:, i] = col
    
    
    



fig, ax = plt.subplots(figsize=(20, 12), constrained_layout=True)

#pcm = ax.pcolormesh(X, Z, T_smooth, cmap="turbo", shading="auto")

# Contourf suave
levels = np.arange(0, 26, 0.05)  # suavidad cada 1°C

cf = ax.contourf(X, Z, T_ext, levels=levels, cmap= cmocean.cm.thermal)

# Isotermas (líneas negras)
contours = [5, 10, 12, 14, 16, 18, 20, 22]
cs = ax.contour(X, Z, T_ext, levels=contours, colors="k", linewidths=1)
ax.clabel(cs, fmt="%.0f", fontsize=30)


ax.fill_between(
    xi,                # eje X
    bathy_line_plot,   # límite inferior (batimetría)
    Z.max(),           # límite superior
    facecolor="lightgrey",  # relleno gris bonito
    edgecolor="black",      # borde negro
    linewidth=1.5,          # grosor del borde
    zorder=1
)
# ----------------------------------
# 7️⃣ EJES
# ----------------------------------
ax.set_ylim(0, 5000)
ax.invert_yaxis()


ax.set_ylabel("Depth (m)", fontsize=30)
ax.tick_params(axis='both', which='major', labelsize=30)

# Latitudes abajo
lat_ticks_idx = np.linspace(0, len(x)-1, len(lats_st))
ax.set_xticks(lat_ticks_idx)
ax.set_xticklabels([f"{lat:.2f}°N" for lat in lats_st], rotation=45, ha='right')
ax.set_xlabel("Latitude", fontsize=30)

### puntos
ax.scatter(
    X_data[mask],
    Z_data[mask],
    facecolors="white",
    edgecolors="black",
    s=20,
    linewidth=0.5,
    zorder=3
)


# Estaciones arriba

# Número de columnas de X (todos los puntos)
n_points = X.shape[1]

# Índices exactos de las estaciones dentro de X
station_idx = np.linspace(0, n_points-1, len(names_st), dtype=int)


ax_top = ax.twiny()
ax_top.set_xlim(ax.get_xlim())
ax_top.set_xticks(lat_ticks_idx)  # mismos índices que latitudes
ax_top.set_xticklabels(names_st, fontsize=30)
ax_top.set_xlabel("Station", fontsize=30)
ax_top.tick_params(axis='x', labelsize=30)

# ----------------------------------
# 8️⃣ COLORBAR
# ----------------------------------
cbar = fig.colorbar(cf, ax=ax, orientation='vertical')
cbar.set_label("Temperature (°C)", fontsize=30)
cbar.ax.tick_params(labelsize=30)
cbar.set_ticks(np.arange(0, 26, 5))

plt.title(f"Temperature Section (Copernicus) – {today}", fontsize=30)


plt.show()


TSec_path = os.path.join(out_path, "TSec.png")
fig.savefig(TSec_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como CHLgeo.png")


##### Salinity


S_ext = S_smooth.copy()
Z_max = 6000

for i in range(S_ext.shape[1]):
    col = S_ext[:, i]
    valid_idx = np.where(~np.isnan(col))[0]
    if len(valid_idx) == 0:
        continue
    last_valid = valid_idx[-1]
    col[last_valid:] = col[last_valid]
    S_ext[:, i] = col

# --- 2️⃣ Graficar ---
fig, ax = plt.subplots(figsize=(20, 12), constrained_layout=True)

# Contourf suave de salinidad
levels = np.arange(34, 38, 0.01)  # ajusta rango según tus datos
cf = ax.contourf(X, Z, S_ext, levels=levels, cmap=cmocean.cm.haline)

# Isolíneas de salinidad
contours = [34.5, 35, 35.5, 35.75,36, 36.5, 37]
cs = ax.contour(X, Z, S_ext, levels=contours, colors="k", linewidths=1)
ax.clabel(cs, fmt="%.2f", fontsize=30)

# Batimetría gris con borde negro
ax.fill_between(
    xi,                # eje X (transecto)
    bathy_line_plot,   # límite inferior (batimetría)
    Z.max(),           # límite superior
    facecolor="lightgrey",
    edgecolor="black",
    linewidth=1.5,
    zorder=1
)

# ----------------------------------
# Ejes
# ----------------------------------
ax.set_ylim(0, 5000)
ax.invert_yaxis()
ax.set_ylabel("Depth (m)", fontsize=30)
ax.tick_params(axis='both', which='major', labelsize=30)

# Latitudes abajo
lat_ticks_idx = np.linspace(0, len(x)-1, len(lats_st))
ax.set_xticks(lat_ticks_idx)
ax.set_xticklabels([f"{lat:.2f}°N" for lat in lats_st], rotation=45, ha='right')
ax.set_xlabel("Latitude", fontsize=30)

# Puntos de CTD
ax.scatter(
    X_data[mask],
    Z_data[mask],
    facecolors="white",
    edgecolors="black",
    s=20,
    linewidth=0.5,
    zorder=3
)

# Estaciones arriba
ax_top = ax.twiny()
ax_top.set_xlim(ax.get_xlim())
ax_top.set_xticks(lat_ticks_idx)
ax_top.set_xticklabels(names_st, fontsize=30)
ax_top.set_xlabel("Station", fontsize=30)
ax_top.tick_params(axis='x', labelsize=30)

# ----------------------------------
# Colorbar
# ----------------------------------
cbar = fig.colorbar(cf, ax=ax, orientation='vertical')
cbar.set_label("Salinity", fontsize=30)
cbar.ax.tick_params(labelsize=30)
cbar.set_ticks(np.arange(34, 38, 0.5))

# Título
plt.title(f"Salinity Section (Copernicus) – {today}", fontsize=30)

# Guardar figura
Ssec_path = os.path.join(out_path, "Ssec.png")
fig.savefig(Ssec_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como Ssec.png")


######## Oxygen

Ox_ext = Ox_smooth.copy()
Z_max = 6000

Ox_ext = Ox_ext * 22.391 * 1e-3
print("Rango en ml/L:", np.nanmin(Ox_ext), "-", np.nanmax(Ox_ext))

for i in range(Ox_ext.shape[1]):
    col = Ox_ext[:, i]
    valid_idx = np.where(~np.isnan(col))[0]
    if len(valid_idx) == 0:
        continue
    last_valid = valid_idx[-1]
    col[last_valid:] = col[last_valid]
    Ox_ext[:, i] = col
    
    
vmin = np.nanmin(Ox_ext)
vmax = np.nanmax(Ox_ext)

# ----------------------------------------
# 2️⃣ Graficar sección de oxígeno
# ----------------------------------------
fig, ax = plt.subplots(figsize=(20, 12), constrained_layout=True)

# Contourf suave
levels = np.arange(vmin, vmax, 0.05)  # ajusta según tus datos de oxígeno
cf = ax.contourf(X, Z, Ox_ext, levels=levels, cmap=cmocean.cm.oxy)

# Isolíneas de oxígeno
contours = [1,2,3, 4, 5, 6]
cs = ax.contour(X, Z, Ox_ext, levels=contours, colors="k", linewidths=1)
ax.clabel(cs, fmt="%.2f", fontsize=30)

# Batimetría gris con borde negro
ax.fill_between(
    xi,                # eje X (transecto)
    bathy_line_plot,   # límite inferior (batimetría)
    Z.max(),           # límite superior
    facecolor="lightgrey",
    edgecolor="black",
    linewidth=1.5,
    zorder=1
)

# ----------------------------------
# Ejes
# ----------------------------------
ax.set_ylim(0, 5000)
ax.invert_yaxis()
ax.set_ylabel("Depth (m)", fontsize=30)
ax.tick_params(axis='both', which='major', labelsize=30)

# Latitudes abajo
lat_ticks_idx = np.linspace(0, len(x)-1, len(lats_st))
ax.set_xticks(lat_ticks_idx)
ax.set_xticklabels([f"{lat:.2f}°N" for lat in lats_st], rotation=45, ha='right')
ax.set_xlabel("Latitude", fontsize=30)

# Puntos de CTD
ax.scatter(
    X_data[mask],
    Z_data[mask],
    facecolors="white",
    edgecolors="black",
    s=20,
    linewidth=0.5,
    zorder=3
)

# Estaciones arriba
ax_top = ax.twiny()
ax_top.set_xlim(ax.get_xlim())
ax_top.set_xticks(lat_ticks_idx)
ax_top.set_xticklabels(names_st, fontsize=30)
ax_top.set_xlabel("Station", fontsize=30)
ax_top.tick_params(axis='x', labelsize=30)

# ----------------------------------
# Colorbar
# ----------------------------------
cbar = fig.colorbar(cf, ax=ax, orientation='vertical')
cbar.set_label("Oxygen (ml/L)", fontsize=30)
cbar.ax.tick_params(labelsize=30)
cbar.set_ticks(np.arange(vmin, vmax, 0.5))

# Título
plt.title(f"Oxygen Section (Copernicus) – {today}", fontsize=30)

# ----------------------------------
# Guardar figura
# ----------------------------------
O2sec_path = os.path.join(out_path, "O2sec.png")
fig.savefig(O2sec_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como O2sec.png")


##### clorofila

CHL_ext = CHL_smooth.copy()
Z_max = 6000
for i in range(CHL_ext.shape[1]):
    col = CHL_ext[:, i]
    valid_idx = np.where(~np.isnan(col))[0]
    if len(valid_idx) == 0:
        continue
    last_valid = valid_idx[-1]
    col[last_valid:] = col[last_valid]
    CHL_ext[:, i] = col

# ------------------------
# 6️⃣ Graficar sección
# ------------------------
fig, ax = plt.subplots(figsize=(20, 12), constrained_layout=True)

vmin, vmax = np.nanmin(CHL_ext), np.nanmax(CHL_ext)
levels = np.linspace(vmin, vmax, 100)

cf = ax.contourf(X, Z, CHL_ext, levels=levels, cmap="jet", vmin=vmin, vmax=vmax)

# Isolíneas
contours = np.linspace(vmin, vmax, 7)
cs = ax.contour(X, Z, CHL_ext, levels=contours, colors="k", linewidths=1)
ax.clabel(cs, fmt="%.2f", fontsize=30)

# Batimetría gris con borde negro
ax.fill_between(
    xi,
    bathy_line_plot,
    Z.max(),
    facecolor="lightgrey",
    edgecolor="black",
    linewidth=1.5,
    zorder=1
)

# ----------------------------------
# Ejes
# ----------------------------------
ax.set_ylim(0, 200)
ax.invert_yaxis()
ax.set_ylabel("Depth (m)", fontsize=30)
ax.tick_params(axis='both', which='major', labelsize=30)

lat_ticks_idx = np.linspace(0, len(x)-1, len(lats_st))
ax.set_xticks(lat_ticks_idx)
ax.set_xticklabels([f"{lat:.2f}°N" for lat in lats_st], rotation=45, ha='right')
ax.set_xlabel("Latitude", fontsize=30)

ax.scatter(
    X_data[mask],
    Z_data[mask],
    facecolors="white",
    edgecolors="black",
    s=20,
    linewidth=0.5,
    zorder=3
)

# Estaciones arriba
ax_top = ax.twiny()
ax_top.set_xlim(ax.get_xlim())
ax_top.set_xticks(lat_ticks_idx)
ax_top.set_xticklabels(names_st, fontsize=30)
ax_top.set_xlabel("Station", fontsize=30)
ax_top.tick_params(axis='x', labelsize=30)

# Colorbar
cbar = fig.colorbar(cf, ax=ax, orientation='vertical')
cbar.set_label("Chlorophyll a (mg/m³)", fontsize=30)
cbar.ax.tick_params(labelsize=30)

plt.title(f"Chlorophyll a Section (Copernicus) – {today}", fontsize=30)

# Guardar figura
CHLsec_path = os.path.join(out_path, "CHLsec.png")
fig.savefig(CHLsec_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como CHLsec.png")
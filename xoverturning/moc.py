import xarray as xr
from xoverturning.compfunc import (
    substract_hml,
    rotate_velocities_to_geo,
    interp_to_grid_center,
    select_basins,
    compute_streamfunction,
)


def calcmoc(
    ds,
    dsgrid=None,
    basin="global",
    rotate=False,
    remove_hml=False,
    add_offset=False,
    mask_output=False,
    offset=0.1,
    rho0=1035.0,
    layer="z_l",
    interface="z_i",
    model="mom6",
    umo="umo",
    vmo="vmo",
    uhml="uhml",
    vhml="vhml",
    verbose=True,
):
    """Compute Meridional Overturning

    Args:
        ds (xarray.Dataset): input dataset. It should contain at least
                             umo, vmo and some grid information
        dsgrid (xarray.Dataset): grid dataset. It should contain at least
                             lon/lat/mask
        basin (str, optional): Basin to use (global/atl-arc/indopac). Defaults to "global".
        rotate (bool, optional): Rotate velocities to true North. Defaults to False.
        remove_hml (bool, optional): Substract Thickness Flux to Restratify Mixed Layer.
                                     Defaults to False.
        add_offset (bool, optional): Add offset to clean up zero contours in plot. Defaults to False.
        mask_output (bool, optional): mask ocean floor, only for Z-coordinates
        offset (float, optional): offset for contours, should be small. Defaults to 0.1.
        rho0 (float, optional): Average density of seawater. Defaults to 1035.0.
        layer (str, optional): Vertical dimension for layers. Defaults to "z_l".
        interface (str, optional): Vertical dimension for interfaces. Defaults to "z_i".
        model (str, optional): ocean model used, currently only mom6 is supported.
        umo (str, optional): override for transport name. Defaults to "umo".
        vmo (str, optional): override for transport name. Defaults to "vmo".
        uhml (str, optional): overide for thickness flux. Defaults to "uhml".
        vhml (str, optional): override for thickness flux. Defaults to "vhml".
        verbose (bool, optional): verbose output. Defaults to True.

    Returns:
        xarray.DataArray: meridional overturning
    """

    names = define_names(model=model)

    if dsgrid is not None:
        ds = merge_grid_dataset(ds, dsgrid, names)

    if remove_hml:
        ucorr, vcorr = substract_hml(ds, umo=umo, vmo=vmo, uhml=uhml, vhml=vhml)
    else:
        ucorr, vcorr = ds[umo], ds[vmo]

    if rotate:
        u_ctr, v_ctr = rotate_velocities_to_geo(ds, ucorr, vcorr)
    else:
        u_ctr, v_ctr = ucorr, vcorr

    if (names["y_corner"] in v_ctr.dims) and (names["x_center"] in v_ctr.dims):
        lon, lat, mask = names["lon_v"], names["lat_v"], names["mask_v"]
    elif (names["y_center"] in v_ctr.dims) and (names["x_center"] in v_ctr.dims):
        lon, lat, mask = names["lon_t"], names["lat_t"], names["mask_t"]

    maskbasin, maskmoc = select_basins(
        ds,
        basin=basin,
        lon=lon,
        lat=lat,
        mask=mask,
        bathy=names["bathy"],
        verbose=verbose,
    )

    ds_v = xr.Dataset()
    ds_v["v"] = v_ctr.where(maskbasin)
    for var in [
        names["x_center"],
        names["y_center"],
        names["x_corner"],
        names["y_corner"],
        layer,
        interface,
    ]:
        ds_v[var] = ds[var]

    moc = compute_streamfunction(
        ds_v,
        xdim=names["x_center"],
        layer=layer,
        interface=interface,
        rho0=rho0,
        add_offset=add_offset,
        offset=offset,
    )

    if mask_output:
        moc = moc.where(maskmoc)

    return moc


def define_names(model="mom6"):
    """ define names for coordinates and variables according to model """

    if model == "mom6":
        names = dict(
            x_center="xh",
            y_center="yh",
            x_corner="xq",
            y_corner="yq",
            lon_t="geolon",
            lat_t="geolat",
            mask_t="wet",
            lon_v="geolon_v",
            lat_v="geolat_v",
            mask_v="wet_v",
            bathy="deptho",
        )
    return names


def merge_grid_dataset(ds, dsgrid, names):
    """ merge grid and transports dataset into one """

    for coord in dsgrid.coords:
        ds[coord] = dsgrid[coord]

    for k, v in names.items():
        ds[v] = dsgrid[v]

    return ds

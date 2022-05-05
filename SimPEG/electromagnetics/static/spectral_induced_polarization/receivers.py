import numpy as np
# import properties
from ....utils import sdiag, validate_string_property, validate_float_property

from ....survey import BaseTimeRx


class BaseRx(BaseTimeRx):
    """
    Base spectral IP receiver class

    Parameters
    ----------
    locations : (n_loc, dim) np.ndarray
        Receiver locations.
    times : numpy.array_like
        Time channels
    orientation : str, default = ``None``
        Receiver orientation. Must be one of: ``None``, 'x', 'y' or 'z'
    data_type : str, default = 'volt'
        Data type. Choose one of: "volt", "apparent_resistivity", "apparent_chargeability"
    projField : str, default = 'phi'
        Fields solved on the mesh. Choose one of: "phi", "e", "j"
    """

    def __init__(self, locations=None, times=None, data_type='volt', orientation=None, projField="phi", **kwargs):
        super(BaseRx, self).__init__(locations=locations, times=times, **kwargs)

        self.orientation = orientation
        self.data_type = data_type
        self.projField = projField

    # orientation = properties.StringChoice(
    #     "orientation of the receiver. Must currently be 'x', 'y', 'z'", ["x", "y", "z"]
    # )

    @property
    def orientation(self):
        """Orientation of the receiver.

        Returns
        -------
        str
            Orientation of the receiver. One of {None, 'x', 'y', 'z'}
        """
        return self._orientation

    @orientation.setter
    def orientation(self, var):
        if var is not None:
            var = validate_string_property('orientation', var, ('x', 'y', 'z')).lower()
        self._orientation = var

    # projField = properties.StringChoice(
    #     "field to be projected in the calculation of the data",
    #     choices=["phi", "e", "j"],
    #     default="phi",
    # )

    @property
    def projField(self):
        """Fields on the mesh

        Returns
        -------
        str
            Fields defined on mesh. One of {"phi", "e", "j"}
        """
        return self._projField

    @projField.setter
    def projField(self, var):
        var = validate_string_property('projField', var, ('phi', 'e', 'j')).lower()
        self._projField = var

    # data_type = properties.StringChoice(
    #     "Type of DC-IP survey",
    #     required=True,
    #     default="volt",
    #     choices=["volt", "apparent_resistivity", "apparent_chargeability"],
    # )

    @property
    def data_type(self):
        """Data type; i.e. "volt", "apparent_resistivity", "apparent_chargeability"

        Returns
        -------
        str
            Data type; i.e. "volt", "apparent_resistivity", "apparent_chargeability"
        """
        return self._data_type

    @data_type.setter
    def data_type(self, var):
        var = validate_string_property('data_type', var).lower()
        if var in ("potential", "potentials", "volt", "v", "voltages", "voltage"):
            self._data_type = 'volt'
        elif var in ("apparent resistivity","appresistivity","apparentresistivity","apparent-resistivity","apparent_resistivity","appres"):
            self._data_type = 'apparent_resistivity'
        elif var in ("apparent chargeability","appchargeability","apparentchargeability","apparent-chargeability","apparent_chargeability"):
            self._data_type = 'apparent_chargeability'
        else:
            raise ValueError(f"data_type must be either 'volt', 'apparent_resistivity' or 'apparent_chargeability'. Got {var}")


    # @property
    # def projField(self):
    #     """Field Type projection (e.g. e b ...)"""
    #     return self.knownRxTypes[self.rxType][0]

    @property
    def dc_voltage(self):
        """DC voltage

        Returns
        -------
        numpy.ndarray
            DC data for each receiver
        """
        return self._dc_voltage

    # def projected_grid(self, f):
    #     """Grid Location projection (e.g. Ex Fy ...)"""
    #     if self.orientation is not None:
    #         return f._GLoc(self.projField) + self.orientation
    #     return f._GLoc(self.projField)

    def getTimeP(self, times_all):
        """Returns the time projection matrix.

        This is not stored in memory, but is created on demand.

        Parameters
        ----------
        times_all : numpy.ndarray
            All times using the time-stepping

        Returns
        -------
        numpy.ndarray
            Time projection from time-steps to time channels
        """
        time_inds = np.in1d(times_all, self.times)
        return time_inds

    def eval(self, src, mesh, f):
        """Project fields to receivers to get data.

        Parameters
        ----------
        src : SimPEG.electromagnetics.static.spectral_induced_polarization.sources.BaseRx
            A spectral IP receiver
        mesh : discretize.base.BaseMesh
            The mesh on which the discrete set of equations is solved
        f : SimPEG.electromagnetic.static.spectral_induced_polarization.Fields
            The solution for the fields defined on the mesh
        
        Returns
        -------
        np.ndarray
            Fields projected to the receiver(s)
        """
        if self.orientation is not None:
            projected_grid = f._GLoc(self.projField) + self.orientation
        else:
            projected_grid = f._GLoc(self.projField)

        P = self.getP(mesh, projected_grid)
        proj_f = self.projField
        if proj_f == "phi":
            proj_f = "phiSolution"
        return P * f[src, proj_f]

    def evalDeriv(self, src, mesh, f, v, adjoint=False):
        """Derivative of projected fields with respect to the inversion model times a vector.

        Parameters
        ----------
        src : SimPEG.electromagnetics.static.spectral_induced_polarization.sources.BaseRx
            A spectral IP receiver
        mesh : discretize.base.BaseMesh
            The mesh on which the discrete set of equations is solved
        f : SimPEG.electromagnetic.static.spectral_induced_polarization.Fields
            The solution for the fields defined on the mesh
        v : np.ndarray
            A vector
        adjoint : bool, default = ``False``
            If ``True``, return the adjoint
        
        Returns
        -------
        np.ndarray
            derivative of fields times a vector projected to the receiver(s)
        """
        if self.orientation is not None:
            projected_grid = f._GLoc(self.projField) + self.orientation
        else:
            projected_grid = f._GLoc(self.projField)

        P = self.getP(mesh, projected_grid)
        if not adjoint:
            return P * v
        elif adjoint:
            return P.T * v


class Dipole(BaseRx):
    """
    Spectral IP dipole receiver class

    Parameters
    ----------
    locations_m : (n_loc, dim) numpy.ndarray
        M electrode locations; remember to set 'locations_n' keyword argument to define N electrode locations.
    locations_n : (n_loc, dim) numpy.ndarray
        N electrode locations; remember to set 'locations_m' keyword argument to define M electrode locations.
    locations : list or tuple of length 2 of np.ndarray
        M and N electrode locations. In this case, do not set the 'locations_m' and 'locations_n'
        keyword arguments. And we supply a list or tuple of the form [locations_m, locations_n].
    orientation : str, default = ``None``
        Receiver orientation. Must be one of: ``None``, 'x', 'y' or 'z'
    data_type : str, default = 'volt'
        Data type. Choose one of: "volt", "apparent_resistivity", "apparent_chargeability"
    """

    # locations = properties.List(
    #     "list of locations of each electrode in a dipole receiver",
    #     RxLocationArray("location of electrode", shape=("*", "*")),
    #     min_length=1,
    #     max_length=2,
    # )

    def __init__(
        self, locations_m=None, locations_n=None, times=None, locations=None, **kwargs
    ):
        # Check for old keywords
        if "locationsM" in kwargs.keys():
            locations_m = kwargs.pop("locationsM")
            raise TypeError(
                "The locationsM property has been removed Please set the "
                "locations_m property instead."
            )

        if "locationsN" in kwargs.keys():
            locations_n = kwargs.pop("locationsN")
            raise TypeError(
                "The locationsN property has been deprecated. Please set the "
                "locations_n property instead"
            )

        # if locations_m set, then use locations_m, locations_n
        if locations_m is not None:
            if locations_n is None:
                raise ValueError(
                    "For a dipole source both locations_m and locations_n "
                    "must be set"
                )

            if locations is not None:
                raise ValueError(
                    "Cannot set both locations and locations_m, locations_n. "
                    "Please provide either locations=(locations_m, locations_n) "
                    "or both locations_m=locations_m, locations_n=locations_n"
                )

            locations = [np.atleast_2d(locations_m), np.atleast_2d(locations_n)]

        if locations is None:
            raise AttributeError(
                "Receiver cannot be instantiated without assigning 'locations'."
                "Please provide either locations=(locations_m, locations_n) "
                "or both locations_m=locations_m, locations_n=locations_n"
            )

        super().__init__(locations=locations, times=times, **kwargs)

    # @property
    # def locations_m(self):
    #     """Locations of the M-electrodes"""
    #     return self.locations[0]

    # @property
    # def locations_n(self):
    #     """Locations of the N-electrodes"""
    #     return self.locations[1]

    @property
    def locations(self):
        """M and N electrode locations

        Returns
        -------
        list of 2 (n_loc, dim) np.ndarray
            M and N electrode locations.
        """
        return self._locations

    @locations.setter
    def locations(self, locs):
        if len(locs) != 2:
            raise ValueError(
                    "locations must be a list or tuple of length 2: "
                    "[locations_m, locations_n]. The input locations has "
                    f"length {len(locs)}"
                )
        
        locs = [np.atleast_2d(locs[0]), np.atleast_2d(locs[1])]

        # check the size of locations_m, locations_n
        if locs[0].shape != locs[1].shape:
            raise ValueError(
                f"locations_m (shape: {locs[0].shape}) and "
                f"locations_n (shape: {locs[1].shape}) need to be "
                f"the same size"
            )
            
        self._locations = locs

    @property
    def locations_m(self):
        """Locations of the M-electrodes

        Returns
        -------
        (n, dim) numpy.ndarray
            Locations of the M-electrodes
        """
        return self.locations[0]

    @property
    def locations_n(self):
        """Locations of the N-electrodes

        Returns
        -------
        (n, dim) numpy.ndarray
            Locations of the N-electrodes
        """
        return self.locations[1]

    # this should probably be updated to n_receivers...
    @property
    def nD(self):
        """Number of data associate with the receiver(s).

        Returns
        -------
        int
            Number of data associated with the receiver(s).
        """
        return self.locations[0].shape[0]

    def getP(self, mesh, projected_grid):
        """
        Get projection matrix from mesh to receivers

        Parameters
        ----------
        mesh : discretize.base.BaseMesh
            The mesh on which the discrete set of equations is solved
        projected_grid : str
            Tensor locations on the mesh being interpolated from. *projected_grid* must be one of:

            - 'Ex', 'edges_x'           -> x-component of field defined on x edges
            - 'Ey', 'edges_y'           -> y-component of field defined on y edges
            - 'Ez', 'edges_z'           -> z-component of field defined on z edges
            - 'Fx', 'faces_x'           -> x-component of field defined on x faces
            - 'Fy', 'faces_y'           -> y-component of field defined on y faces
            - 'Fz', 'faces_z'           -> z-component of field defined on z faces
            - 'N', 'nodes'              -> scalar field defined on nodes
            - 'CC', 'cell_centers'      -> scalar field defined on cell centers
            - 'CCVx', 'cell_centers_x'  -> x-component of vector field defined on cell centers
            - 'CCVy', 'cell_centers_y'  -> y-component of vector field defined on cell centers
            - 'CCVz', 'cell_centers_z'  -> z-component of vector field defined on cell centers

        Returns
        -------
        scipy.sparse.csr_matrix
            P, the interpolation matrix

        """
        if mesh in self._Ps:
            return self._Ps[mesh]

        P0 = mesh.get_interpolation_matrix(self.locations[0], projected_grid)
        P1 = mesh.get_interpolation_matrix(self.locations[1], projected_grid)
        P = P0 - P1

        if self.data_type == "apparent_resistivity":
            P = sdiag(1.0 / self.geometric_factor) * P
        elif self.data_type == "apparent_chargeability":
            P = sdiag(1.0 / self.dc_voltage) * P

        if self.storeProjections:
            self._Ps[mesh] = P

        return P


class Pole(BaseRx):
    """
    Spectral IP pole receiver class

    Parameters
    ----------
    locations : (n_loc, dim) np.ndarray
        Receiver locations. 
    orientation : str, default = ``None``
        Receiver orientation. Must be one of: ``None``, 'x', 'y' or 'z'
    data_type : str, default = 'volt'
        Data type. Choose one of: "volt", "apparent_resistivity", "apparent_chargeability"
    """

    # this should probably be updated to n_receivers...
    @property
    def nD(self):
        """Number of data associate with the receiver(s).

        Returns
        -------
        int
            Number of data associated with the receiver(s).
        """
        return self.locations.shape[0]

    def getP(self, mesh, projected_grid):
        """
        Get projection matrix from mesh to receivers

        Parameters
        ----------
        mesh : discretize.base.BaseMesh
            The mesh on which the discrete set of equations is solved
        projected_grid : str
            Tensor locations on the mesh being interpolated from. *projected_grid* must be one of:

            - 'Ex', 'edges_x'           -> x-component of field defined on x edges
            - 'Ey', 'edges_y'           -> y-component of field defined on y edges
            - 'Ez', 'edges_z'           -> z-component of field defined on z edges
            - 'Fx', 'faces_x'           -> x-component of field defined on x faces
            - 'Fy', 'faces_y'           -> y-component of field defined on y faces
            - 'Fz', 'faces_z'           -> z-component of field defined on z faces
            - 'N', 'nodes'              -> scalar field defined on nodes
            - 'CC', 'cell_centers'      -> scalar field defined on cell centers
            - 'CCVx', 'cell_centers_x'  -> x-component of vector field defined on cell centers
            - 'CCVy', 'cell_centers_y'  -> y-component of vector field defined on cell centers
            - 'CCVz', 'cell_centers_z'  -> z-component of vector field defined on cell centers

        Returns
        -------
        scipy.sparse.csr_matrix
            P, the interpolation matrix

        """
        if mesh in self._Ps:
            return self._Ps[mesh]

        P = mesh.get_interpolation_matrix(self.locations, projected_grid)

        if self.data_type == "apparent_resistivity":
            P = sdiag(1.0 / self.geometric_factor) * P
        elif self.data_type == "apparent_chargeability":
            P = sdiag(1.0 / self.dc_voltage) * P

        if self.storeProjections:
            self._Ps[mesh] = P

        return P

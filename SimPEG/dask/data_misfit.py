from ..data_misfit import L2DataMisfit
from ..fields import Fields
from ..utils import mkvc
import dask.array as da
from scipy.sparse import csr_matrix as csr
from dask import delayed


def dask_call(self, m, f=None):
    """
    Distributed :obj:`simpeg.data_misfit.L2DataMisfit.__call__`
    """
    R = self.W * self.residual(m, f=f)
    phi_d = 0.5 * da.dot(R, R)
    if self.workers is None:
        return phi_d.compute()
    return self.client.compute(phi_d, workers=self.workers)


L2DataMisfit.__call__ = dask_call


def dask_deriv(self, m, f=None):
    """
    Distributed :obj:`simpeg.data_misfit.L2DataMisfit.deriv`
    """

    if getattr(self, "model_map", None) is not None:
        m = self.model_map @ m

    wtw_d = self.W.diagonal() ** 2.0 * self.residual(m, f=f)
    Jtvec = self.simulation.Jtvec(m, wtw_d)

    if getattr(self, "model_map", None) is not None:
        Jtjvec_dmudm = delayed(csr.dot)(Jtvec, self.model_map.deriv(m))
        h_vec = da.from_delayed(
            Jtjvec_dmudm, dtype=float, shape=[self.model_map.deriv(m).shape[1]]
        )
        if self.workers is None:
            return h_vec.compute()
        return self.client.compute(h_vec, workers=self.workers)

    if self.workers is None:
        return Jtvec.compute()
    return self.client.compute(Jtvec, workers=self.workers)


L2DataMisfit.deriv = dask_deriv


def dask_deriv2(self, m, v, f=None):
    """
    Distributed :obj:`simpeg.data_misfit.L2DataMisfit.deriv2`
    """

    if getattr(self, "model_map", None) is not None:
        m = self.model_map @ m
        v = self.model_map.deriv(m) @ v

    jvec = self.simulation.Jvec(m, v)
    w_jvec = self.W.diagonal() ** 2.0 * jvec
    jtwjvec = self.simulation.Jtvec(m, w_jvec)

    if getattr(self, "model_map", None) is not None:
        Jtjvec_dmudm = delayed(csr.dot)(jtwjvec, self.model_map.deriv(m))
        h_vec = da.from_delayed(
            Jtjvec_dmudm, dtype=float, shape=[self.model_map.deriv(m).shape[1]]
        )
        if self.workers is None:
            return h_vec.compute()
        return self.client.compute(h_vec, workers=self.workers)

    if self.workers is None:
        return jtwjvec.compute()
    return self.client.compute(jtwjvec, workers=self.workers)


L2DataMisfit.deriv2 = dask_deriv2


def dask_residual(self, m, f=None):
    if self.data is None:
        raise Exception("data must be set before a residual can be calculated.")

    if isinstance(f, Fields) or f is None:
        return self.simulation.residual(m, self.data.dobs, f=f)
    elif f.shape == self.data.dobs.shape:
        return mkvc(f - self.data.dobs)
    else:
        raise Exception(f"Attribute f must be or type {Fields}, numpy.array or None.")


L2DataMisfit.residual = dask_residual
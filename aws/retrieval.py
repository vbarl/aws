import numpy as np

from aws.simulation import Simulation
from aws.sensor import CloudSat
from artssat.jacobian import Log10
from artssat.data_provider import DataProviderBase

class RainAPriori(DataProviderBase):
    def __init__(self):
        super().__init__()

    def get_rain_water_content_xa(self, *args, **kwargs):
        t = self.owner.get_temperature(*args, **kwargs)
        xa = np.zeros(t.shape)
        xa[:] = 1e-5
        xa[t < 273.15] = 1e-12
        return np.log10(xa)

    def get_rain_water_content_covariance(self, *args, **kwargs):
        t = self.owner.get_temperature(*args, **kwargs)
        diag = 2.0 * np.ones(t.size)
        diag[t < 273.15] = 1e-24
        covmat = np.diag(diag)
        return covmat

    def get_rain_n0(self, *args, **kwargs):
        t = self.owner.get_temperature(*args, **kwargs)
        return 1e7 * np.ones(t.shape)

class IceAPriori(DataProviderBase):
    def __init__(self):
        super().__init__()

    def get_ice_water_content_xa(self, *args, **kwargs):
        t = self.owner.get_temperature(*args, **kwargs)
        xa = np.zeros(t.shape)
        xa[:] = 1e-5
        xa[t >= 273.15] = 1e-12
        return np.log10(xa)

    def get_ice_water_content_covariance(self, *args, **kwargs):
        t = self.owner.get_temperature(*args, **kwargs)
        diag = 2.0 * np.ones(t.size)
        diag[t >= 273.15] = 1e-12
        covmat = np.diag(diag)
        return covmat

    def get_ice_n0(self, *args, **kwargs):
        t = self.owner.get_temperature(*args, **kwargs)
        t = t - 273.15
        return np.exp(-0.076586 * t + 17.948)

class ObservationErrors(DataProviderBase):
    def __init__(self, nedt=1.0):
        super().__init__()
        self.nedt = 1.0

    def get_observation_error_covariance(self, *args, **kwargs):
        range_bins = self.owner.get_cloudsat_range_bins(*args, **kwargs)
        return np.diag(self.nedt * np.ones(range_bins.size - 1))


class Retrieval(Simulation, DataProviderBase):
    def __init__(self,
                 data_provider,
                 ice_shape = "8-ColumnAggregate"):
        sensor = CloudSat()

        data_provider.add(IceAPriori())
        data_provider.add(RainAPriori())
        data_provider.add(ObservationErrors())
        self.data_provider = data_provider

        DataProviderBase.__init__(self)
        Simulation.__init__(self,
                            sensor,
                            data_provider,
                            ice_shape=ice_shape)

        scatterers = self.atmosphere.scatterers
        # Add first moment ice to retrieval and set transform
        ice = [s for s in scatterers if s.name == "ice"][0]
        self.retrieval.add(ice.moments[0])
        ice.moments[0].transformation = Log10()
        self._ice_water_content = ice.moments[0]

        # Add first moment of rain PSD to retrieval and set transform
        rain = [s for s in scatterers if s.name == "rain"][0]
        self.retrieval.add(rain.moments[0])
        rain.moments[0].transformation = Log10()
        self._rain_water_content = rain.moments[0]

        self.iwc = [None] * data_provider.n_profiles
        self.rwc = [None] * data_provider.n_profiles

        self.retrieval.settings["stop_dx"] = 1e-6
        self.setup()

    def run(self, i, silent=False):

        self.retrieval.settings["display_progress"] = int(not silent)
        Simulation.run(self, i)
        self.iwc[i] = self.retrieval.results.get_result(self._ice_water_content,
                                                        transform_back=True)
        self.rwc[i] = self.retrieval.results.get_result(self._rain_water_content,
                                                        transform_back=True)

    def get_ice_water_content(self, i):
        if self.iwc[i] is None:
            self.run(i, silent=True)
        return self.iwc[i]

    def get_rain_water_content(self, i):
        if self.rwc[i] is None:
            self.run(i, silent=True)
        return self.rwc[i]

    def __setstate__(self, state):
        self.__dict__ = state
        self.setup()

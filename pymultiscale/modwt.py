# This is a Python port of portions of the waveslim package for R.
#
#   http://cran.r-project.org/web/packages/waveslim/index.html
#
# Waveslim was written by Brandon Whitcher <bwhitcher@gmail.com>.
# This Python port was written by Michael Broxton
# <broxton@stanford.edu>.
#
# This code and is licensed under the GPL (v2 or above).
#
# At the moment only the 2D and 3D undecimated wavelet transform and its
# inverse have been wrapped in Python.  However, it would be easy to
# wrap the the 1D, 2D, and 3D DWT, as well as the 1D, and 2D UDWT.
# The C code for doing so is already compiled as part of this module,
# and the code below could serve as a guide for wrapping these other
# functions.

import numpy as np

def modwt_transform(data, wavelet_type = 'd8', num_bands = None):
        '''
        Perform a maximal overlap discrete wavelet transform (MODWT),
        which is very closely related to the 3D undecimated
        (i.e. stationary) wavelet transform.

        Arguments:

            data - A 1D, 2D, or 3D numpy array to be transformed.

        Returns:

            coefs - A python list containing (7 * num_bands + 1) entries.
                    Each successive set of 7 entries contain the
                    directional wavelet coefficient (HHH, HLL, LHL, LLH,
                    HHL, HLH, LHH) for increasingly coarse wavelet bands.
                    The final entry contains the final low-pass image (LLL)
                    at the end of the filter bank.

        '''

        ndims = len(data.shape)

        if data.dtype != np.float64:
            data = data.astype(np.float64, order = 'F')

        if num_bands == None:
            num_bands = int(np.ceil(np.log2(np.min(data.shape))) - 3)
            assert num_bands > 0

        if ndims == 1:
            from pymultiscale.dwt import modwt1
            return modwt1(data, wavelet_type, num_bands)
        elif ndims == 2:
            from pymultiscale.dwt import modwt2
            return modwt2(data, wavelet_type, num_bands)
        elif ndims == 3:
            from pymultiscale.dwt import modwt3
            return modwt3(data, wavelet_type, num_bands)
        else:
            raise NotImplementedError("MODWT not supported for %dD data." % (len(data.shape)))


def inverse_modwt_transform(coefs, wavelet_type):
    ndims = len(coefs[0].shape)
    if ndims == 1:
        from pymultiscale.dwt import imodwt1
        return imodwt1(coefs, wavelet_type)
    elif ndims == 2:
        from pymultiscale.dwt import imodwt2
        return imodwt2(coefs, wavelet_type)
    elif ndims == 3:
        from pymultiscale.dwt import imodwt3
        return imodwt3(coefs, wavelet_type)
    else:
        raise NotImplementedError("Inverse MODWT not supported for %dD data." % (len(coefs[0].shape)))

# -----------------------------------------------------------------------------
#                         OBJECT-ORIENTED API
# -----------------------------------------------------------------------------

class UndecimatedWaveletTransform(object):

    def __init__(self, img_shape, wavelet_type, num_bands = None):
        '''
        A class for performing the maximal overlap discrete wavelet
        transform (MODWT), which is very closely related to the 3D
        undecimated (i.e. stationary) wavelet transform.

        Arguments:

           wavelet_type - A string referring to one of the wavelets defined
                          in filters.py. To see the complete list, run.

                            from wavelets/filters import list_filters
                            list_filters()

              num_bands - Sets the number of bands to compute in the decomposition.
                          If 'None' is provided, then num_bands is automatically
                          set to:

                             int( ceil( log2( min(data.shape) ) ) - 3)
        '''

        # Store wavelet type
        self.wavelet_type = wavelet_type
        self.num_bands = num_bands
        self.img_shape = img_shape

        # Run a test tranform to determine the structure of
        # the lists containing the coefficients.  This is used
        # when reconstituting the coefficients from a flattened vector
        # of coefs, and vice versa.
        self.example_coefs = self.fwd(np.zeros(img_shape))

    # ------------- Forward and inverse transforms ------------------

    def fwd(self, data):
        '''
        Perform a maximal overlap discrete wavelet transform (MODWT),
        which is very closely related to the 3D undecimated
        (i.e. stationary) wavelet transform.

        Arguments:

            data - A 1D, 2D, or 3D numpy array to be transformed.

        Returns:

            coefs - A python list containing (7 * num_bands + 1) entries.
                    Each successive set of 7 entries contain the
                    directional wavelet coefficient (HHH, HLL, LHL, LLH,
                    HHL, HLH, LHH) for increasingly coarse wavelet bands.
                    The final entry contains the final low-pass image (LLL)
                    at the end of the filter bank.

        '''
        return modwt_transform(data, self.wavelet_type, self.num_bands)


    def inv(self, coefs):
        return inverse_modwt_transform(coefs, self.wavelet_type)

    # --------------------- Utility methods -------------------------

    def num_bands(self, coefs):
        if len(coefs[0].shape) == 2:
            return (len(coefs)-1)/3
        elif len(coefs[0].shape) == 2:
            return (len(coefs)-1)/7
        else:
            raise NotImplementedError("UDWT num_bands() not supported for %dD data." % (len(data.shape)))

    def num_coefficients(self):
        return len(self.example_coefs) * np.prod(self.example_coefs[0].shape)

    def num_nonzero_coefficients(self, coefs):
        return sum([ band.nonzero()[0].shape[0] for band in coefs ])

    def coefs_to_vec(self, coefs):
        return np.hstack([vec.ravel(order = 'f') for vec in coefs])

    def vec_to_coefs(self, coef_vec):
        return [np.reshape(vec, self.img_shape, order = 'f') for vec in np.split(coef_vec, len(self.example_coefs))]

    def update(self, coefs, update, alpha):
        '''
        Adds the update (multiplied by alpha) to each set of
        coefficients.
        '''

        # Check arguments
        assert len(coefs) == len(update)

        update_squared_sum = 0.0;
        for b in xrange(len(coefs)):
            delta = alpha * update[b]
            coefs[b] += delta
            update_squared_sum += np.square(delta).sum()

        update_norm = np.sqrt(update_squared_sum)
        return (coefs, update_norm)

    def multiplicative_update(self, coefs, numerator, denominator, normalization, alpha):
        '''
        Multiplies the update to each set of coefficients, updating
        them in place.
        '''

        # Check arguments
        assert len(coefs) == len(numerator) == len(denominator)
        for b in xrange(len(coefs)):
            coefs[b] = ((coefs[b] * numerator[b]) / normalization[b]) / (denominator[b] + alpha)
        return coefs

    def set_coefs(self, coefs, value):
        for b in xrange(len(coefs)):
            coefs[b].fill(value)

    def mean(self, coefs):
        '''
        Compute the average over all wavelet coefficients.
        '''
        n        = sum( [ np.prod(coef.shape) for coef in coefs] )
        coef_sum = sum( [ coef.sum()          for coef in coefs] )
        return  coef_sum / n

    # ------------------ Thresholding methods -----------------------

    def threshold_by_band(self, coefs, threshold_func, skip_bands = [], within_axis = None, scaling_factor = None):
        '''
        Threshold each band individually.  The threshold_func() should
        take an array of coefficients (which may be 1d or 2d or 3d),
        and return a tuple: (band_center, band_threshold)

        If you want to threshold within a particular plane within a band,
        set within_axis to that plane.

        Note that the low frequency band is left untouched.

        For the sake of speed and memory efficiency, updates to the
        coefficients are performed in-place.
        '''

        # Store number of dimensions
        ndims = len(coefs[0].shape)
        if ndims == 1:
            ndirections = 1
        elif ndims == 2:
            ndirections = 3
        elif ndims == 3:
            ndirections = 7
        else:
            raise NotImplementedError("UDWT not supported for %dD data." % (ndims))

        # Compute the number of bands, but skip the final LLL image.
        for b in xrange(len(coefs) - 1):

            # UDWT coefficients are stored in groups of 7 (3D)
            band_level = int(np.floor(b/7))

            # Skip band?
            if band_level in skip_bands:
                continue

            if within_axis != None:
                num_planes = coefs[b].shape[within_axis]
                for p in xrange(num_planes):
                    if within_axis == 0:
                        A = coefs[b][p,:,:]
                    elif within_axis == 1:
                        A = coefs[b][:,p,:]
                    else:
                        A = coefs[b][:,:,p]

                    # The undecimated wavelet transform is not
                    # centered... i.e. the coefficients shift along
                    # each dimension in a band-dependent fashion.  The
                    # offset is 2^(wavelet_band), and we must factor
                    # that in here when computing the plane we pass to
                    # threshold_func.
                    #
                    # We also check to make sure to wrap around at the
                    # edges.
                    roll_offset = np.power(2, band_level + 1)
                    adjusted_plane = p - roll_offset
                    if adjusted_plane >= num_planes:
                        adjusted_plane -= num_planes
                    if adjusted_plane < 0:
                        adjusted_plane += num_planes

                    (band_center, band_threshold) = threshold_func(A, band_level, adjusted_plane)
                    if scaling_factor != None:
                        band_threshold /= scaling_factor

                    # Zero out any coefficients that are more than
                    # band_threshold units away from band_center.
                    idxs = np.where( np.abs( A - band_center ) < band_threshold )
                    A[idxs] = 0.0

                    # Soft threshold the coefficients
                    idxs = np.where( A > band_threshold )
                    A[idxs] -= band_threshold
                    idxs = np.where( np.abs(A) <= band_threshold )
                    A[idxs] = 0.0
                    idxs = np.where( A < -band_threshold )
                    A[idxs] += band_threshold

            else:
                (band_center, band_threshold) = threshold_func(coefs[b], band_level, None)
                if scaling_factor != None:
                    band_threshold /= scaling_factor

                # Soft threshold the coefficients
                idxs = np.where( coefs[b] > band_threshold )
                coefs[b][idxs] -= band_threshold
                idxs = np.where( np.abs(coefs[b]) <= band_threshold )
                coefs[b][idxs] = 0.
                idxs = np.where( coefs[b] < -band_threshold )
                coefs[b][idxs] += band_threshold

                # Zero out any coefficients that are more than
                # band_threshold units away from band_center.
                #idxs = np.where( np.abs( coefs[b] - band_center ) < band_threshold )
                #coefs[b][idxs] = 0.0

        return coefs


    def low_pass_spatial_filter(self, coefs, within_axis = 2, range = (0, 0), max_band = 1 ):

        # Compute the number of bands, but skip the final LLL image.
        num_bands = len(coefs) - 1
        for b in xrange(num_bands):

            # There are seven directions per band level
            band_level = int(np.floor(b/7))
            num_planes = coefs[b].shape[within_axis]

            for p in xrange(num_planes):

                if within_axis == 0:
                    A = coefs[b][p,:,:]
                elif within_axis == 1:
                    A = coefs[b][:,p,:]
                else:
                    A = coefs[b][:,:,p]

                if p > range[0] and p < range[1] and band_level < max_band:
                    A[:,:] = 0
        return coefs

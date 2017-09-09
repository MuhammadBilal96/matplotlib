"""
Testing that skewed axes properly work
"""
from __future__ import absolute_import, division, print_function

import itertools

import matplotlib.pyplot as plt
from matplotlib.testing.decorators import image_comparison

from matplotlib.axes import Axes
import matplotlib.transforms as transforms
import matplotlib.axis as maxis
import matplotlib.spines as mspines
import matplotlib.patches as mpatch
from matplotlib.projections import register_projection


# The sole purpose of this class is to look at the upper, lower, or total
# interval as appropriate and see what parts of the tick to draw, if any.
class SkewXTick(maxis.XTick):
    def update_position(self, loc):
        # This ensures that the new value of the location is set before
        # any other updates take place
        self._loc = loc
        super(SkewXTick, self).update_position(loc)

    def _has_default_loc(self):
        return self.get_loc() is None

    def _need_lower(self):
        return (self._has_default_loc() or
                transforms.interval_contains(self.axes.lower_xlim,
                                             self.get_loc()))

    def _need_upper(self):
        return (self._has_default_loc() or
                transforms.interval_contains(self.axes.upper_xlim,
                                             self.get_loc()))

    @property
    def gridOn(self):
        return (self._gridOn and (self._has_default_loc() or
                transforms.interval_contains(self.get_view_interval(),
                                             self.get_loc())))

    @gridOn.setter
    def gridOn(self, value):
        self._gridOn = value

    @property
    def tick1On(self):
        return self._tick1On and self._need_lower()

    @tick1On.setter
    def tick1On(self, value):
        self._tick1On = value

    @property
    def label1On(self):
        return self._label1On and self._need_lower()

    @label1On.setter
    def label1On(self, value):
        self._label1On = value

    @property
    def tick2On(self):
        return self._tick2On and self._need_upper()

    @tick2On.setter
    def tick2On(self, value):
        self._tick2On = value

    @property
    def label2On(self):
        return self._label2On and self._need_upper()

    @label2On.setter
    def label2On(self, value):
        self._label2On = value

    def get_view_interval(self):
        return self.axes.xaxis.get_view_interval()


# This class exists to provide two separate sets of intervals to the tick,
# as well as create instances of the custom tick
class SkewXAxis(maxis.XAxis):
    def _get_tick(self, major):
        return SkewXTick(self.axes, None, '', major=major)

    def get_view_interval(self):
        return self.axes.upper_xlim[0], self.axes.lower_xlim[1]


# This class exists to calculate the separate data range of the
# upper X-axis and draw the spine there. It also provides this range
# to the X-axis artist for ticking and gridlines
class SkewSpine(mspines.Spine):
    def _adjust_location(self):
        pts = self._path.vertices
        if self.spine_type == 'top':
            pts[:, 0] = self.axes.upper_xlim
        else:
            pts[:, 0] = self.axes.lower_xlim


# This class handles registration of the skew-xaxes as a projection as well
# as setting up the appropriate transformations. It also overrides standard
# spines and axes instances as appropriate.
class SkewXAxes(Axes):
    # The projection must specify a name.  This will be used be the
    # user to select the projection, i.e. ``subplot(111,
    # projection='skewx')``.
    name = 'skewx'

    def _init_axis(self):
        # Taken from Axes and modified to use our modified X-axis
        self.xaxis = SkewXAxis(self)
        self.spines['top'].register_axis(self.xaxis)
        self.spines['bottom'].register_axis(self.xaxis)
        self.yaxis = maxis.YAxis(self)
        self.spines['left'].register_axis(self.yaxis)
        self.spines['right'].register_axis(self.yaxis)

    def _gen_axes_spines(self):
        spines = {'top': SkewSpine.linear_spine(self, 'top'),
                  'bottom': mspines.Spine.linear_spine(self, 'bottom'),
                  'left': mspines.Spine.linear_spine(self, 'left'),
                  'right': mspines.Spine.linear_spine(self, 'right')}
        return spines

    def _set_lim_and_transforms(self):
        """
        This is called once when the plot is created to set up all the
        transforms for the data, text and grids.
        """
        rot = 30

        # Get the standard transform setup from the Axes base class
        Axes._set_lim_and_transforms(self)

        # Need to put the skew in the middle, after the scale and limits,
        # but before the transAxes. This way, the skew is done in Axes
        # coordinates thus performing the transform around the proper origin
        # We keep the pre-transAxes transform around for other users, like the
        # spines for finding bounds
        self.transDataToAxes = (self.transScale +
                                (self.transLimits +
                                 transforms.Affine2D().skew_deg(rot, 0)))

        # Create the full transform from Data to Pixels
        self.transData = self.transDataToAxes + self.transAxes

        # Blended transforms like this need to have the skewing applied using
        # both axes, in axes coords like before.
        self._xaxis_transform = (transforms.blended_transform_factory(
            self.transScale + self.transLimits,
            transforms.IdentityTransform()) +
            transforms.Affine2D().skew_deg(rot, 0)) + self.transAxes

    @property
    def lower_xlim(self):
        return self.axes.viewLim.intervalx

    @property
    def upper_xlim(self):
        pts = [[0., 1.], [1., 1.]]
        return self.transDataToAxes.inverted().transform(pts)[:, 0]


# Now register the projection with matplotlib so the user can select
# it.
register_projection(SkewXAxes)


@image_comparison(baseline_images=['skew_axes'], remove_text=True)
def test_set_line_coll_dash_image():
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, projection='skewx')
    ax.set_xlim(-50, 50)
    ax.set_ylim(50, -50)
    ax.grid(True)

    # An example of a slanted line at constant X
    ax.axvline(0, color='b')


@image_comparison(baseline_images=['skew_rects'], remove_text=True)
def test_skew_rectangle():

    fix, axes = plt.subplots(5, 5, sharex=True, sharey=True, figsize=(16, 12))
    axes = axes.flat

    rotations = list(itertools.product([-3, -1, 0, 1, 3], repeat=2))

    axes[0].set_xlim([-4, 4])
    axes[0].set_ylim([-4, 4])
    axes[0].set_aspect('equal')

    for ax, (xrots, yrots) in zip(axes, rotations):
        xdeg, ydeg = 45 * xrots, 45 * yrots
        t = transforms.Affine2D().skew_deg(xdeg, ydeg)

        ax.set_title('Skew of {0} in X and {1} in Y'.format(xdeg, ydeg))
        ax.add_patch(mpatch.Rectangle([-1, -1], 2, 2,
                                      transform=t + ax.transData,
                                      alpha=0.5, facecolor='coral'))

    plt.subplots_adjust(wspace=0, left=0, right=1, bottom=0)

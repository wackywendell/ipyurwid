#!/usr/bin/env python
# encoding: utf-8
"""
A base class for objects that are configurable.

Authors:

* Brian Granger
* Fernando Perez
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2010  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from copy import deepcopy
import datetime
from weakref import WeakValueDictionary

from IPython.utils.importstring import import_item
from loader import Config
from IPython.utils.traitlets import HasTraits, Instance


#-----------------------------------------------------------------------------
# Helper classes for Configurables
#-----------------------------------------------------------------------------


class ConfigurableError(Exception):
    pass


#-----------------------------------------------------------------------------
# Configurable implementation
#-----------------------------------------------------------------------------


class Configurable(HasTraits):

    config = Instance(Config,(),{})
    created = None

    def __init__(self, **kwargs):
        """Create a conigurable given a config config.

        Parameters
        ----------
        config : Config
            If this is empty, default values are used. If config is a 
            :class:`Config` instance, it will be used to configure the
            instance.
        
        Notes
        -----
        Subclasses of Configurable must call the :meth:`__init__` method of
        :class:`Configurable` *before* doing anything else and using 
        :func:`super`::
        
            class MyConfigurable(Configurable):
                def __init__(self, config=None):
                    super(MyConfigurable, self).__init__(config)
                    # Then any other code you need to finish initialization.

        This ensures that instances will be configured properly.
        """
        config = kwargs.pop('config', None)
        if config is not None:
            # We used to deepcopy, but for now we are trying to just save
            # by reference.  This *could* have side effects as all components
            # will share config. In fact, I did find such a side effect in
            # _config_changed below. If a config attribute value was a mutable type
            # all instances of a component were getting the same copy, effectively
            # making that a class attribute.
            # self.config = deepcopy(config)
            self.config = config
        # This should go second so individual keyword arguments override 
        # the values in config.
        super(Configurable, self).__init__(**kwargs)
        self.created = datetime.datetime.now()

    #-------------------------------------------------------------------------
    # Static trait notifiations
    #-------------------------------------------------------------------------

    def _config_changed(self, name, old, new):
        """Update all the class traits having ``config=True`` as metadata.

        For any class trait with a ``config`` metadata attribute that is
        ``True``, we update the trait with the value of the corresponding
        config entry.
        """
        # Get all traits with a config metadata entry that is True
        traits = self.traits(config=True)

        # We auto-load config section for this class as well as any parent
        # classes that are Configurable subclasses.  This starts with Configurable
        # and works down the mro loading the config for each section.
        section_names = [cls.__name__ for cls in \
            reversed(self.__class__.__mro__) if 
            issubclass(cls, Configurable) and issubclass(self.__class__, cls)]

        for sname in section_names:
            # Don't do a blind getattr as that would cause the config to 
            # dynamically create the section with name self.__class__.__name__.
            if new._has_section(sname):
                my_config = new[sname]
                for k, v in traits.iteritems():
                    # Don't allow traitlets with config=True to start with
                    # uppercase.  Otherwise, they are confused with Config
                    # subsections.  But, developers shouldn't have uppercase
                    # attributes anyways! (PEP 6)
                    if k[0].upper()==k[0] and not k.startswith('_'):
                        raise ConfigurableError('Configurable traitlets with '
                        'config=True must start with a lowercase so they are '
                        'not confused with Config subsections: %s.%s' % \
                        (self.__class__.__name__, k))
                    try:
                        # Here we grab the value from the config
                        # If k has the naming convention of a config
                        # section, it will be auto created.
                        config_value = my_config[k]
                    except KeyError:
                        pass
                    else:
                        # print "Setting %s.%s from %s.%s=%r" % \
                        #     (self.__class__.__name__,k,sname,k,config_value)
                        # We have to do a deepcopy here if we don't deepcopy the entire
                        # config object. If we don't, a mutable config_value will be
                        # shared by all instances, effectively making it a class attribute.
                        setattr(self, k, deepcopy(config_value))


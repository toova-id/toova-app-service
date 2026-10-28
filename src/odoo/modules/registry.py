# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Models registries.

"""
from collections import defaultdict, deque
from collections.abc import Mapping
from contextlib import closing, contextmanager
from functools import partial
import gc
import json
from operator import attrgetter
import inspect
import logging
import os
import threading
import time
import warnings

import psycopg2

import odoo
from odoo.modules.db import FunctionStatus
from odoo.osv.expression import get_unaccent_wrapper
from .. import SUPERUSER_ID
from odoo.sql_db import TestCursor
from odoo.tools import (config, existing_tables, lazy_classproperty,
                        lazy_property, sql, Collector, OrderedSet)
from odoo.tools.func import locked
from odoo.tools.lru import LRU

_logger = logging.getLogger(__name__)
_cache_logger = logging.getLogger(__name__ + '.cache')
_schema = logging.getLogger('odoo.schema')

_SIGNALING_CHANNEL = 'odoo_registry_signaling'
_SIGNALING_SEQUENCES_SQL = """ SELECT base_registry_signaling.last_value,
                                      base_cache_signaling.last_value
                               FROM base_registry_signaling, base_cache_signaling"""
_signal_state = {}
_signal_state_lock = threading.RLock()
_signal_listener_lock = threading.Lock()
_signal_listeners = {}
_preload_heap_frozen = False


class _NullTestResult:
    def __init__(self):
        self.testsRun = 0
        self.shouldStop = False

    def update(self, other):
        self.testsRun += other.testsRun

    def wasSuccessful(self):
        return True

    def log_stats(self):
        pass


def mark_preload_heap_frozen():
    global _preload_heap_frozen
    _preload_heap_frozen = True

def unfreeze_preload_heap():
    """Release permanent-generation references before runtime registry replacement."""
    global _preload_heap_frozen
    if _preload_heap_frozen and hasattr(gc, 'unfreeze'):
        gc.unfreeze()
        _preload_heap_frozen = False
        return True
    return False


def update_signaling_state(db_name, registry=None, cache=None):
    """Advance locally observed generations; delayed notifications cannot move state back."""
    with _signal_state_lock:
        old_registry, old_cache = _signal_state.get(db_name, (None, None))
        _signal_state[db_name] = (
            max(old_registry, registry) if old_registry is not None and registry is not None else
            registry if registry is not None else old_registry,
            max(old_cache, cache) if old_cache is not None and cache is not None else
            cache if cache is not None else old_cache,
        )
        return _signal_state[db_name]


def reconcile_signaling_state(db_name, registry, cache):
    """Replace state from authoritative PostgreSQL sequences, including after DB restore."""
    with _signal_state_lock:
        _signal_state[db_name] = registry, cache
        return _signal_state[db_name]

def get_signaling_state(db_name):
    with _signal_state_lock:
        return _signal_state.get(db_name, (None, None))


class SignalingListener:
    """Listen on one database channel; PostgreSQL notifications are per-database."""

    def __init__(self, db_name):
        self.db_name = db_name
        self.pid = None
        self.thread = None
        self.stop_event = threading.Event()
        self.connected = False
        self.last_reconcile = 0.0

    def start(self):
        if self.thread and self.thread.is_alive() and self.pid == os.getpid():
            return
        self.pid = os.getpid()
        self.stop_event = threading.Event()
        self.connected = False
        self.last_reconcile = 0.0
        self.thread = threading.Thread(
            target=self.run, name='odoo.registry.signaling.%s' % self.db_name, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def run(self):
        import select

        delay = 1
        while not self.stop_event.is_set() and self.pid == os.getpid():
            connection = None
            try:
                connection = odoo.sql_db.db_connect_signaling(self.db_name)
                connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                cursor = connection.cursor()
                try:
                    cursor.execute('LISTEN ' + _SIGNALING_CHANNEL)
                    self.reconcile(connection)
                    self.connected = True
                    delay = 1
                    _logger.info('Registry signaling listener connected on %s.', self.db_name)
                    while not self.stop_event.is_set():
                        if select.select([connection], [], [], 1)[0]:
                            connection.poll()
                            while connection.notifies:
                                notification = connection.notifies.pop(0)
                                if self.consume(notification.payload):
                                    self.reconcile(connection)
                        if time.monotonic() - self.last_reconcile >= config['registry_signaling_reconcile_seconds']:
                            self.reconcile(connection)
                finally:
                    cursor.close()
            except Exception:
                self.connected = False
                _logger.warning('Registry signaling listener on %s disconnected; retrying in %ss.',
                                self.db_name, delay, exc_info=True)
                self.stop_event.wait(delay)
                delay = min(delay * 2, 60)
            finally:
                self.connected = False
                if connection is not None:
                    connection.close()

    def consume(self, payload):
        """Consume one notification and report whether a generation gap needs reconciliation."""
        try:
            data = json.loads(payload)
            if data.get('db') != self.db_name:
                raise ValueError
            generations = [data.get(key) for key in ('registry', 'cache') if data.get(key) is not None]
            if not generations or any(not isinstance(value, int) or value < 1 for value in generations):
                raise ValueError
            old_registry, old_cache = get_signaling_state(self.db_name)
            gap = ((data.get('registry') is not None and old_registry is not None and
                    data['registry'] > old_registry + 1) or
                   (data.get('cache') is not None and old_cache is not None and
                    data['cache'] > old_cache + 1))
            update_signaling_state(data['db'], data.get('registry'), data.get('cache'))
            return gap
        except (KeyError, TypeError, ValueError):
            _logger.warning('Ignoring invalid registry signaling payload.')
            return False

    def reconcile(self, connection):
        """Read authoritative generations over the durable LISTEN connection."""
        with connection.cursor() as cursor:
            cursor.execute(_SIGNALING_SEQUENCES_SQL)
            reconcile_signaling_state(self.db_name, *cursor.fetchone())
        self.last_reconcile = time.monotonic()

def start_signaling_listener(db_name):
    listener = _signal_listeners.get(db_name)
    if listener is not None and listener.pid == os.getpid() and listener.thread.is_alive():
        return listener
    with _signal_listener_lock:
        listener = _signal_listeners.get(db_name)
        if listener is None or listener.pid != os.getpid():
            listener = SignalingListener(db_name)
            _signal_listeners[db_name] = listener
        listener.start()
        return listener

def stop_signaling_listener():
    with _signal_listener_lock:
        for listener in _signal_listeners.values():
            listener.stop()

def reset_signaling_after_fork():
    global _signal_listeners, _signal_listener_lock, _signal_state
    _signal_listener_lock = threading.Lock()
    _signal_listeners = {}
    _signal_state = {}


class Registry(Mapping):
    """ Model registry for a particular database.

    The registry is essentially a mapping between model names and model classes.
    There is one registry instance per database.

    """
    _lock = threading.RLock()
    _saved_lock = None

    @lazy_classproperty
    def registries(cls):
        """ A mapping from database names to registries. """
        size = config.get('registry_lru_size', None)
        if not size:
            # Size the LRU depending of the memory limits
            if os.name != 'posix':
                # cannot specify the memory limit soft on windows...
                size = 42
            else:
                # A registry takes 10MB of memory on average, so we reserve
                # 10Mb (registry) + 5Mb (working memory) per registry
                avgsz = 15 * 1024 * 1024
                size = int(config['limit_memory_soft'] / avgsz)
        return LRU(size)

    def __new__(cls, db_name):
        """ Return the registry for the given database name."""
        with cls._lock:
            try:
                return cls.registries[db_name]
            except KeyError:
                return cls.new(db_name)

    @classmethod
    @locked
    def new(cls, db_name, force_demo=False, status=None, update_module=False):
        """ Create and return a new registry for the given database name. """
        t0 = time.time()
        registry = object.__new__(cls)
        registry.init(db_name)
        registry.new = registry.init = registry.registries = None

        # Initializing a registry will call general code which will in
        # turn call Registry() to obtain the registry being initialized.
        # Make it available in the registries dictionary then remove it
        # if an exception is raised.
        cls.delete(db_name)
        cls.registries[db_name] = registry  # pylint: disable=unsupported-assignment-operation
        try:
            registry.setup_signaling()
            # This should be a method on Registry
            try:
                odoo.modules.load_modules(registry, force_demo, status, update_module)
            except Exception:
                odoo.modules.reset_modules_state(db_name)
                raise
        except Exception:
            _logger.exception('Failed to load registry')
            del cls.registries[db_name]     # pylint: disable=unsupported-delete-operation
            raise

        # load_modules() above can replace the registry by calling
        # indirectly new() again (when modules have to be uninstalled).
        # Yeah, crazy.
        registry = cls.registries[db_name]  # pylint: disable=unsubscriptable-object

        registry._init = False
        registry.ready = True
        registry.registry_invalidated = bool(update_module)

        field_count = sum(len(model._fields) for model in registry.models.values())
        _logger.info("Registry loaded in %.3fs: %d models, %d fields",
                     time.time() - t0, len(registry.models), field_count)
        return registry

    def init(self, db_name):
        self.models = {}    # model name/model instance mapping
        self._sql_constraints = set()
        self._init = True
        self._database_translated_fields = ()  # names of translated fields in database
        if config['test_enable'] or config['test_file']:
            from odoo.tests.result import OdooTestResult
            self._assertion_report = OdooTestResult()
        else:
            self._assertion_report = _NullTestResult()
        self._fields_by_model = None
        self._ordinary_tables = None
        self._constraint_queue = deque()
        self.__cache = LRU(8192)

        # modules fully loaded (maintained during init phase by `loading` module)
        self._init_modules = set()
        self.updated_modules = []       # installed/updated modules
        self.loaded_xmlids = set()

        self.db_name = db_name
        self._db = odoo.sql_db.db_connect(db_name)

        # cursor for test mode; None means "normal" mode
        self.test_cr = None
        self.test_lock = None

        # Indicates that the registry is
        self.loaded = False             # whether all modules are loaded
        self.ready = False              # whether everything is set up

        # field dependencies
        self.field_depends = Collector()
        self.field_depends_context = Collector()
        self.field_inverses = Collector()

        # cache of methods get_field_trigger_tree() and is_modifying_relations()
        self._field_trigger_trees = {}
        self._is_modifying_relations = {}

        # Inter-process signaling:
        # The `base_registry_signaling` sequence indicates the whole registry
        # must be reloaded.
        # The `base_cache_signaling sequence` indicates all caches must be
        # invalidated (i.e. cleared).
        self.registry_sequence = None
        self.cache_sequence = None

        # Flags indicating invalidation of the registry or the cache.
        self._invalidation_flags = threading.local()

        with closing(self.cursor()) as cr:
            self.has_unaccent = odoo.modules.db.has_unaccent(cr)
            self.has_trigram = odoo.modules.db.has_trigram(cr)

    @classmethod
    @locked
    def delete(cls, db_name):
        """ Delete the registry linked to a given database. """
        if db_name in cls.registries:  # pylint: disable=unsupported-membership-test
            del cls.registries[db_name]  # pylint: disable=unsupported-delete-operation

    @classmethod
    @locked
    def delete_all(cls):
        """ Delete all the registries. """
        cls.registries.clear()

    #
    # Mapping abstract methods implementation
    # => mixin provides methods keys, items, values, get, __eq__, and __ne__
    #
    def __len__(self):
        """ Return the size of the registry. """
        return len(self.models)

    def __iter__(self):
        """ Return an iterator over all model names. """
        return iter(self.models)

    def __getitem__(self, model_name):
        """ Return the model with the given name or raise KeyError if it doesn't exist."""
        return self.models[model_name]

    def __call__(self, model_name):
        """ Same as ``self[model_name]``. """
        return self.models[model_name]

    def __setitem__(self, model_name, model):
        """ Add or replace a model in the registry."""
        self.models[model_name] = model

    def __delitem__(self, model_name):
        """ Remove a (custom) model from the registry. """
        del self.models[model_name]
        # the custom model can inherit from mixins ('mail.thread', ...)
        for Model in self.models.values():
            Model._inherit_children.discard(model_name)

    def descendants(self, model_names, *kinds):
        """ Return the models corresponding to ``model_names`` and all those
        that inherit/inherits from them.
        """
        assert all(kind in ('_inherit', '_inherits') for kind in kinds)
        funcs = [attrgetter(kind + '_children') for kind in kinds]

        models = OrderedSet()
        queue = deque(model_names)
        while queue:
            model = self[queue.popleft()]
            models.add(model._name)
            for func in funcs:
                queue.extend(func(model))
        return models

    def load(self, cr, module):
        """ Load a given module in the registry, and return the names of the
        modified models.

        At the Python level, the modules are already loaded, but not yet on a
        per-registry level. This method populates a registry with the given
        modules, i.e. it instantiates all the classes of a the given module
        and registers them in the registry.

        """
        from .. import models

        # clear cache to ensure consistency, but do not signal it
        self.__cache.clear()

        lazy_property.reset_all(self)
        self._field_trigger_trees.clear()
        self._is_modifying_relations.clear()

        # Instantiate registered classes (via the MetaModel automatic discovery
        # or via explicit constructor call), and add them to the pool.
        model_names = []
        for cls in models.MetaModel.module_to_models.get(module.name, []):
            # models register themselves in self.models
            model = cls._build_model(self, cr)
            model_names.append(model._name)

        return self.descendants(model_names, '_inherit', '_inherits')

    @locked
    def setup_models(self, cr):
        """ Complete the setup of models.
            This must be called after loading modules and before using the ORM.
        """
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        env.invalidate_all()

        # Uninstall registry hooks. Because of the condition, this only happens
        # on a fully loaded registry, and not on a registry being loaded.
        if self.ready:
            for model in env.values():
                model._unregister_hook()

        # clear cache to ensure consistency, but do not signal it
        self.__cache.clear()

        lazy_property.reset_all(self)
        self._field_trigger_trees.clear()
        self._is_modifying_relations.clear()
        self.registry_invalidated = True

        # we must setup ir.model before adding manual fields because _add_manual_models may
        # depend on behavior that is implemented through overrides, such as is_mail_thread which
        # is implemented through an override to env['ir.model']._instanciate
        env['ir.model']._prepare_setup()

        # add manual models
        if self._init_modules:
            env['ir.model']._add_manual_models()

        # prepare the setup on all models
        models = list(env.values())
        for model in models:
            model._prepare_setup()

        self.field_depends.clear()
        self.field_depends_context.clear()
        self.field_inverses.clear()

        # do the actual setup
        for model in models:
            model._setup_base()

        self._m2m = defaultdict(list)
        for model in models:
            model._setup_fields()
        del self._m2m

        for model in models:
            model._setup_complete()

        # determine field_depends and field_depends_context
        for model in models:
            for field in model._fields.values():
                depends, depends_context = field.get_depends(model)
                self.field_depends[field] = tuple(depends)
                self.field_depends_context[field] = tuple(depends_context)

        # clean the lazy_property again in case they are cached by another ongoing registry readonly request
        lazy_property.reset_all(self)

        # Reinstall registry hooks. Because of the condition, this only happens
        # on a fully loaded registry, and not on a registry being loaded.
        if self.ready:
            for model in env.values():
                model._register_hook()
            env.flush_all()

    @lazy_property
    def field_computed(self):
        """ Return a dict mapping each field to the fields computed by the same method. """
        computed = {}
        for model_name, Model in self.models.items():
            groups = defaultdict(list)
            for field in Model._fields.values():
                if field.compute:
                    computed[field] = group = groups[field.compute]
                    group.append(field)
            for fields in groups.values():
                if len({field.compute_sudo for field in fields}) > 1:
                    _logger.warning("%s: inconsistent 'compute_sudo' for computed fields: %s",
                                    model_name, ", ".join(field.name for field in fields))
                if len({field.precompute for field in fields}) > 1:
                    _logger.warning("%s: inconsistent 'precompute' for computed fields: %s",
                                    model_name, ", ".join(field.name for field in fields))
        return computed

    def get_trigger_tree(self, fields: list, select=bool) -> "TriggerTree":
        """ Return the trigger tree to traverse when ``fields`` have been modified.
        The function ``select`` is called on every field to determine which fields
        should be kept in the tree nodes.  This enables to discard some unnecessary
        fields from the tree nodes.
        """
        trees = [
            self.get_field_trigger_tree(field)
            for field in fields
            if field in self._field_triggers
        ]
        return TriggerTree.merge(trees, select)

    def get_dependent_fields(self, field):
        """ Return an iterable on the fields that depend on ``field``. """
        if field not in self._field_triggers:
            return ()

        return (
            dependent
            for tree in self.get_field_trigger_tree(field).depth_first()
            for dependent in tree.root
        )

    def _discard_fields(self, fields: list):
        """ Discard the given fields from the registry's internal data structures. """
        for f in fields:
            # tests usually don't reload the registry, so when they create
            # custom fields those may not have the entire dependency setup, and
            # may be missing from these maps
            self.field_depends.pop(f, None)

        # discard fields from field triggers
        self.__dict__.pop('_field_triggers', None)
        self._field_trigger_trees.clear()
        self._is_modifying_relations.clear()

        # discard fields from field inverses
        self.field_inverses.discard_keys_and_values(fields)

    def get_field_trigger_tree(self, field) -> "TriggerTree":
        """ Return the trigger tree of a field by computing it from the transitive
        closure of field triggers.
        """
        try:
            return self._field_trigger_trees[field]
        except KeyError:
            pass

        triggers = self._field_triggers

        if field not in triggers:
            return TriggerTree()

        def transitive_triggers(field, prefix=(), seen=()):
            if field in seen or field not in triggers:
                return
            for path, targets in triggers[field].items():
                full_path = concat(prefix, path)
                yield full_path, targets
                for target in targets:
                    yield from transitive_triggers(target, full_path, seen + (field,))

        def concat(seq1, seq2):
            if seq1 and seq2:
                f1, f2 = seq1[-1], seq2[0]
                if (
                    f1.type == 'many2one' and f2.type == 'one2many'
                    and f1.name == f2.inverse_name
                    and f1.model_name == f2.comodel_name
                    and f1.comodel_name == f2.model_name
                ):
                    return concat(seq1[:-1], seq2[1:])
            return seq1 + seq2

        tree = TriggerTree()
        for path, targets in transitive_triggers(field):
            current = tree
            for label in path:
                current = current.increase(label)
            if current.root:
                current.root.update(targets)
            else:
                current.root = OrderedSet(targets)

        self._field_trigger_trees[field] = tree

        return tree

    @lazy_property
    def _field_triggers(self):
        """ Return the field triggers, i.e., the inverse of field dependencies,
        as a dictionary like ``{field: {path: fields}}``, where ``field`` is a
        dependency, ``path`` is a sequence of fields to inverse and ``fields``
        is a collection of fields that depend on ``field``.
        """
        triggers = defaultdict(lambda: defaultdict(OrderedSet))

        for Model in self.models.values():
            if Model._abstract:
                continue
            for field in Model._fields.values():
                try:
                    dependencies = list(field.resolve_depends(self))
                except Exception:
                    # dependencies of custom fields may not exist; ignore that case
                    if not field.base_field.manual:
                        raise
                else:
                    for dependency in dependencies:
                        *path, dep_field = dependency
                        triggers[dep_field][tuple(reversed(path))].add(field)

        return triggers

    def is_modifying_relations(self, field):
        """ Return whether ``field`` has dependent fields on some records, and
        that modifying ``field`` might change the dependent records.
        """
        try:
            return self._is_modifying_relations[field]
        except KeyError:
            result = field in self._field_triggers and (
                field.relational or self.field_inverses[field] or any(
                    dep.relational or self.field_inverses[dep]
                    for dep in self.get_dependent_fields(field)
                )
            )
            self._is_modifying_relations[field] = result
            return result

    def post_init(self, func, *args, **kwargs):
        """ Register a function to call at the end of :meth:`~.init_models`. """
        self._post_init_queue.append(partial(func, *args, **kwargs))

    def post_constraint(self, func, *args, **kwargs):
        """ Call the given function, and delay it if it fails during an upgrade. """
        try:
            if (func, args, kwargs) not in self._constraint_queue:
                # Module A may try to apply a constraint and fail but another module B inheriting
                # from Module A may try to reapply the same constraint and succeed, however the
                # constraint would already be in the _constraint_queue and would be executed again
                # at the end of the registry cycle, this would fail (already-existing constraint)
                # and generate an error, therefore a constraint should only be applied if it's
                # not already marked as "to be applied".
                func(*args, **kwargs)
        except Exception as e:
            if self._is_install:
                _schema.error(*e.args)
            else:
                _schema.info(*e.args)
                self._constraint_queue.append((func, args, kwargs))

    def finalize_constraints(self):
        """ Call the delayed functions from above. """
        while self._constraint_queue:
            func, args, kwargs = self._constraint_queue.popleft()
            try:
                func(*args, **kwargs)
            except Exception as e:
                # warn only, this is not a deployment showstopper, and
                # can sometimes be a transient error
                _schema.warning(*e.args)

    def init_models(self, cr, model_names, context, install=True):
        """ Initialize a list of models (given by their name). Call methods
            ``_auto_init`` and ``init`` on each model to create or update the
            database tables supporting the models.

            The ``context`` may contain the following items:
             - ``module``: the name of the module being installed/updated, if any;
             - ``update_custom_fields``: whether custom fields should be updated.
        """
        if not model_names:
            return

        if 'module' in context:
            _logger.info('module %s: creating or updating database tables', context['module'])
        elif context.get('models_to_check', False):
            _logger.info("verifying fields for every extended model")

        env = odoo.api.Environment(cr, SUPERUSER_ID, context)
        models = [env[model_name] for model_name in model_names]

        try:
            self._post_init_queue = deque()
            self._foreign_keys = {}
            self._is_install = install

            for model in models:
                model._auto_init()
                model.init()

            env['ir.model']._reflect_models(model_names)
            env['ir.model.fields']._reflect_fields(model_names)
            env['ir.model.fields.selection']._reflect_selections(model_names)
            env['ir.model.constraint']._reflect_constraints(model_names)

            self._ordinary_tables = None

            while self._post_init_queue:
                func = self._post_init_queue.popleft()
                func()

            self.check_indexes(cr, model_names)
            self.check_foreign_keys(cr)

            env.flush_all()

            # make sure all tables are present
            self.check_tables_exist(cr)

        finally:
            del self._post_init_queue
            del self._foreign_keys
            del self._is_install

    def check_indexes(self, cr, model_names):
        """ Create or drop column indexes for the given models. """
        expected = [
            (f"{Model._table}_{field.name}_index", Model._table, field, getattr(field, 'unaccent', False))
            for model_name in model_names
            for Model in [self.models[model_name]]
            if Model._auto and not Model._abstract
            for field in Model._fields.values()
            if field.column_type and field.store
        ]
        if not expected:
            return

        # retrieve existing indexes with their corresponding table
        cr.execute("SELECT indexname, tablename FROM pg_indexes WHERE indexname IN %s",
                   [tuple(row[0] for row in expected)])
        existing = dict(cr.fetchall())

        for indexname, tablename, field, unaccent in expected:
            column_expression = f'"{field.name}"'
            index = field.index
            assert index in ('btree', 'btree_not_null', 'trigram', True, False, None)
            if index and indexname not in existing and \
                    ((not field.translate and index != 'trigram') or (index == 'trigram' and self.has_trigram)):

                if index == 'trigram':
                    if field.translate:
                        column_expression = f'''(jsonb_path_query_array({column_expression}, '$.*')::text)'''
                    # add `unaccent` to the trigram index only because the
                    # trigram indexes are mainly used for (i/=)like search and
                    # unaccent is added only in these cases when searching
                    if unaccent and self.has_unaccent:
                        if self.has_unaccent == FunctionStatus.INDEXABLE:
                            column_expression = get_unaccent_wrapper(cr)(column_expression)
                        else:
                            warnings.warn(
                                "PostgreSQL function 'unaccent' is present but not immutable, "
                                "therefore trigram indexes may not be effective.",
                            )
                    expression = f'{column_expression} gin_trgm_ops'
                    method = 'gin'
                    where = ''
                else:  # index in ['btree', 'btree_not_null'， True]
                    expression = f'{column_expression}'
                    method = 'btree'
                    where = f'{column_expression} IS NOT NULL' if index == 'btree_not_null' else ''
                try:
                    with cr.savepoint(flush=False):
                        sql.create_index(cr, indexname, tablename, [expression], method, where)
                except psycopg2.OperationalError:
                    _schema.error("Unable to add index for %s", self)

            elif not index and tablename == existing.get(indexname):
                _schema.info("Keep unexpected index %s on table %s", indexname, tablename)

    def add_foreign_key(self, table1, column1, table2, column2, ondelete,
                        model, module, force=True):
        """ Specify an expected foreign key. """
        key = (table1, column1)
        val = (table2, column2, ondelete, model, module)
        if force:
            self._foreign_keys[key] = val
        else:
            self._foreign_keys.setdefault(key, val)

    def check_foreign_keys(self, cr):
        """ Create or update the expected foreign keys. """
        if not self._foreign_keys:
            return

        # determine existing foreign keys on the tables
        query = """
            SELECT fk.conname, c1.relname, a1.attname, c2.relname, a2.attname, fk.confdeltype
            FROM pg_constraint AS fk
            JOIN pg_class AS c1 ON fk.conrelid = c1.oid
            JOIN pg_class AS c2 ON fk.confrelid = c2.oid
            JOIN pg_attribute AS a1 ON a1.attrelid = c1.oid AND fk.conkey[1] = a1.attnum
            JOIN pg_attribute AS a2 ON a2.attrelid = c2.oid AND fk.confkey[1] = a2.attnum
            WHERE fk.contype = 'f' AND c1.relname IN %s
        """
        cr.execute(query, [tuple({table for table, column in self._foreign_keys})])
        existing = {
            (table1, column1): (name, table2, column2, deltype)
            for name, table1, column1, table2, column2, deltype in cr.fetchall()
        }

        # create or update foreign keys
        for key, val in self._foreign_keys.items():
            table1, column1 = key
            table2, column2, ondelete, model, module = val
            deltype = sql._CONFDELTYPES[ondelete.upper()]
            spec = existing.get(key)
            if spec is None:
                sql.add_foreign_key(cr, table1, column1, table2, column2, ondelete)
                conname = sql.get_foreign_keys(cr, table1, column1, table2, column2, ondelete)[0]
                model.env['ir.model.constraint']._reflect_constraint(model, conname, 'f', None, module)
            elif (spec[1], spec[2], spec[3]) != (table2, column2, deltype):
                sql.drop_constraint(cr, table1, spec[0])
                sql.add_foreign_key(cr, table1, column1, table2, column2, ondelete)
                conname = sql.get_foreign_keys(cr, table1, column1, table2, column2, ondelete)[0]
                model.env['ir.model.constraint']._reflect_constraint(model, conname, 'f', None, module)

    def check_tables_exist(self, cr):
        """
        Verify that all tables are present and try to initialize those that are missing.
        """
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        table2model = {
            model._table: name
            for name, model in env.registry.items()
            if not model._abstract and model._table_query is None
        }
        missing_tables = set(table2model).difference(existing_tables(cr, table2model))

        if missing_tables:
            missing = {table2model[table] for table in missing_tables}
            _logger.info("Models have no table: %s.", ", ".join(missing))
            # recreate missing tables
            for name in missing:
                _logger.info("Recreate table of model %s.", name)
                env[name].init()
            env.flush_all()
            # check again, and log errors if tables are still missing
            missing_tables = set(table2model).difference(existing_tables(cr, table2model))
            for table in missing_tables:
                _logger.error("Model %s has no table.", table2model[table])

    def _clear_cache(self):
        """ Clear the cache and mark it as invalidated. """
        debug = _cache_logger.isEnabledFor(logging.DEBUG)
        entries = len(self.__cache) if debug else 0
        self.__cache.clear()
        self.cache_invalidated = True
        if debug:
            frame = inspect.currentframe()
            try:
                caller = frame.f_back
                _cache_logger.debug(
                    "clear db=%s entries=%d caller=%s:%s:%d",
                    self.db_name,
                    entries,
                    caller.f_globals.get('__name__', '?'),
                    caller.f_code.co_name,
                    caller.f_lineno,
                )
            finally:
                del frame

    def clear_caches(self):
        """ Clear the caches associated to methods decorated with
        ``tools.ormcache`` or ``tools.ormcache_multi`` for all the models.
        """
        for model in self.models.values():
            model.clear_caches()

    def is_an_ordinary_table(self, model):
        """ Return whether the given model has an ordinary table. """
        if self._ordinary_tables is None:
            cr = model.env.cr
            query = """
                SELECT c.relname
                  FROM pg_class c
                  JOIN pg_namespace n ON (n.oid = c.relnamespace)
                 WHERE c.relname IN %s
                   AND c.relkind = 'r'
                   AND n.nspname = 'public'
            """
            tables = tuple(m._table for m in self.models.values())
            cr.execute(query, [tables])
            self._ordinary_tables = {row[0] for row in cr.fetchall()}

        return model._table in self._ordinary_tables

    @property
    def registry_invalidated(self):
        """ Determine whether the current thread has modified the registry. """
        return getattr(self._invalidation_flags, 'registry', False)

    @registry_invalidated.setter
    def registry_invalidated(self, value):
        self._invalidation_flags.registry = value

    @property
    def cache_invalidated(self):
        """ Determine whether the current thread has modified the cache. """
        return getattr(self._invalidation_flags, 'cache', False)

    @cache_invalidated.setter
    def cache_invalidated(self, value):
        self._invalidation_flags.cache = value

    def setup_signaling(self):
        """ Setup the inter-process signaling on this registry. """
        if self.in_test_mode():
            return

        start = time.perf_counter()
        with self.cursor() as cr:
            # The `base_registry_signaling` sequence indicates when the registry
            # must be reloaded.
            # The `base_cache_signaling` sequence indicates when all caches must
            # be invalidated (i.e. cleared).
            cr.execute("SELECT sequence_name FROM information_schema.sequences WHERE sequence_name='base_registry_signaling'")
            if not cr.fetchall():
                cr.execute("CREATE SEQUENCE base_registry_signaling INCREMENT BY 1 START WITH 1")
                cr.execute("SELECT nextval('base_registry_signaling')")
                cr.execute("CREATE SEQUENCE base_cache_signaling INCREMENT BY 1 START WITH 1")
                cr.execute("SELECT nextval('base_cache_signaling')")

            cr.execute(_SIGNALING_SEQUENCES_SQL)
            self.registry_sequence, self.cache_sequence = cr.fetchone()
            cr.commit()
            reconcile_signaling_state(self.db_name, self.registry_sequence, self.cache_sequence)
            _logger.debug("Multiprocess load registry signaling: [Registry: %s] [Cache: %s]",
                          self.registry_sequence, self.cache_sequence)
        _logger.info("Registry signaling initialized in %.3fs", time.perf_counter() - start)

    def _reconcile_signaling(self):
        with closing(self.cursor()) as cr:
            cr.execute(_SIGNALING_SEQUENCES_SQL)
            sequences = cr.fetchone()
            cr.rollback()
        reconcile_signaling_state(self.db_name, *sequences)
        return sequences

    def check_signaling(self):
        """ Check whether the registry has changed, and performs all necessary
        operations to update the registry. Return an up-to-date registry.
        """
        if self.in_test_mode():
            return self

        if config['registry_signaling'] == 'event':
            listener = start_signaling_listener(self.db_name)
            r, c = get_signaling_state(self.db_name)
            if not listener.connected or r is None or c is None:
                r, c = self._reconcile_signaling()
        else:
            r, c = self._reconcile_signaling()

        _logger.debug("Multiprocess signaling check: [Registry - %s -> %s] [Cache - %s -> %s]",
                      self.registry_sequence, r, self.cache_sequence, c)
        if self.registry_sequence != r:
            if unfreeze_preload_heap():
                _logger.info("Garbage collector heap unfrozen before registry reload.")
            _logger.info("Reloading the model registry after database signaling.")
            self = Registry.new(self.db_name)
            gc.collect()
            r, c = self.registry_sequence, self.cache_sequence
        elif self.cache_sequence != c:
            _logger.info("Invalidating all model caches after database signaling.")
            self.clear_caches()

        self.cache_invalidated = False
        self.registry_sequence = r
        self.cache_sequence = c
        return self

    def signal_changes(self):
        """ Notifies other processes if registry or cache has been invalidated. """
        if self.registry_invalidated and not self.in_test_mode():
            _logger.info("Registry changed, signaling through the database")
            with closing(self.cursor()) as cr:
                cr.execute("select nextval('base_registry_signaling')")
                self.registry_sequence = cr.fetchone()[0]
                if config['registry_signaling'] == 'event':
                    payload = json.dumps({'db': self.db_name, 'registry': self.registry_sequence})
                    cr.execute("SELECT pg_notify(%s, %s)", [_SIGNALING_CHANNEL, payload])
                    cr.commit()
            update_signaling_state(self.db_name, registry=self.registry_sequence)

        # no need to notify cache invalidation in case of registry invalidation,
        # because reloading the registry implies starting with an empty cache
        elif self.cache_invalidated and not self.in_test_mode():
            _logger.info("At least one model cache has been invalidated, signaling through the database.")
            with closing(self.cursor()) as cr:
                cr.execute("select nextval('base_cache_signaling')")
                self.cache_sequence = cr.fetchone()[0]
                if config['registry_signaling'] == 'event':
                    payload = json.dumps({'db': self.db_name, 'cache': self.cache_sequence})
                    cr.execute("SELECT pg_notify(%s, %s)", [_SIGNALING_CHANNEL, payload])
                    cr.commit()
            update_signaling_state(self.db_name, cache=self.cache_sequence)

        self.registry_invalidated = False
        self.cache_invalidated = False

    def reset_changes(self):
        """ Reset the registry and cancel all invalidations. """
        if self.registry_invalidated:
            with closing(self.cursor()) as cr:
                self.setup_models(cr)
                self.registry_invalidated = False
        if self.cache_invalidated:
            self.__cache.clear()
            self.cache_invalidated = False

    @contextmanager
    def manage_changes(self):
        """ Context manager to signal/discard registry and cache invalidations. """
        try:
            yield self
            self.signal_changes()
        except Exception:
            self.reset_changes()
            raise

    def in_test_mode(self):
        """ Test whether the registry is in 'test' mode. """
        return self.test_cr is not None

    def enter_test_mode(self, cr):
        """ Enter the 'test' mode, where one cursor serves several requests. """
        assert self.test_cr is None
        self.test_cr = cr
        self.test_lock = threading.RLock()
        assert Registry._saved_lock is None
        Registry._saved_lock = Registry._lock
        Registry._lock = DummyRLock()

    def leave_test_mode(self):
        """ Leave the test mode. """
        assert self.test_cr is not None
        self.test_cr = None
        self.test_lock = None
        assert Registry._saved_lock is not None
        Registry._lock = Registry._saved_lock
        Registry._saved_lock = None

    def cursor(self):
        """ Return a new cursor for the database. The cursor itself may be used
            as a context manager to commit/rollback and close automatically.
        """
        if self.test_cr is not None:
            # in test mode we use a proxy object that uses 'self.test_cr' underneath
            return TestCursor(self.test_cr, self.test_lock, current_test=odoo.modules.module.current_test)
        return self._db.cursor()


class DummyRLock(object):
    """ Dummy reentrant lock, to be used while running rpc and js tests """
    def acquire(self):
        pass
    def release(self):
        pass
    def __enter__(self):
        self.acquire()
    def __exit__(self, type, value, traceback):
        self.release()


class TriggerTree(dict):
    """ The triggers of a field F is a tree that contains the fields that
    depend on F, together with the fields to inverse to find out which records
    to recompute.

    For instance, assume that G depends on F, H depends on X.F, I depends on
    W.X.F, and J depends on Y.F. The triggers of F will be the tree:

                                 [G]
                               X/   \\Y
                             [H]     [J]
                           W/
                         [I]

    This tree provides perfect support for the trigger mechanism:
    when F is # modified on records,
     - mark G to recompute on records,
     - mark H to recompute on inverse(X, records),
     - mark I to recompute on inverse(W, inverse(X, records)),
     - mark J to recompute on inverse(Y, records).
    """
    __slots__ = ['root']

    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, root=(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = root

    def __bool__(self):
        return bool(self.root or len(self))

    def increase(self, key):
        try:
            return self[key]
        except KeyError:
            subtree = self[key] = TriggerTree()
            return subtree

    def depth_first(self):
        yield self
        for subtree in self.values():
            yield from subtree.depth_first()

    @classmethod
    def merge(cls, trees: list, select=bool) -> "TriggerTree":
        """ Merge trigger trees into a single tree. The function ``select`` is
        called on every field to determine which fields should be kept in the
        tree nodes. This enables to discard some fields from the tree nodes.
        """
        root_fields = OrderedSet()              # fields in the root node
        subtrees_to_merge = defaultdict(list)   # subtrees to merge grouped by key

        for tree in trees:
            root_fields.update(tree.root)
            for label, subtree in tree.items():
                subtrees_to_merge[label].append(subtree)

        # the root node contains the collected fields for which select is true
        result = cls([field for field in root_fields if select(field)])
        for label, subtrees in subtrees_to_merge.items():
            subtree = cls.merge(subtrees, select)
            if subtree:
                result[label] = subtree

        return result

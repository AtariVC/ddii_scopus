window.pdocSearch = (function () {
	/** elasticlunr - http://weixsong.github.io * Copyright (C) 2017 Oliver Nightingale * Copyright (C) 2017 Wei Song * MIT Licensed */ !(function () {
		function e(e) {
			if (null === e || 'object' != typeof e) return e
			var t = e.constructor()
			for (var n in e) e.hasOwnProperty(n) && (t[n] = e[n])
			return t
		}
		var t = function (e) {
			var n = new t.Index()
			return (
				n.pipeline.add(t.trimmer, t.stopWordFilter, t.stemmer),
				e && e.call(n, n),
				n
			)
		}
		;(t.version = '0.9.5'),
			(lunr = t),
			(t.utils = {}),
			(t.utils.warn = (function (e) {
				return function (t) {
					e.console && console.warn && console.warn(t)
				}
			})(this)),
			(t.utils.toString = function (e) {
				return void 0 === e || null === e ? '' : e.toString()
			}),
			(t.EventEmitter = function () {
				this.events = {}
			}),
			(t.EventEmitter.prototype.addListener = function () {
				var e = Array.prototype.slice.call(arguments),
					t = e.pop(),
					n = e
				if ('function' != typeof t)
					throw new TypeError('last argument must be a function')
				n.forEach(function (e) {
					this.hasHandler(e) || (this.events[e] = []), this.events[e].push(t)
				}, this)
			}),
			(t.EventEmitter.prototype.removeListener = function (e, t) {
				if (this.hasHandler(e)) {
					var n = this.events[e].indexOf(t)
					;-1 !== n &&
						(this.events[e].splice(n, 1),
						0 == this.events[e].length && delete this.events[e])
				}
			}),
			(t.EventEmitter.prototype.emit = function (e) {
				if (this.hasHandler(e)) {
					var t = Array.prototype.slice.call(arguments, 1)
					this.events[e].forEach(function (e) {
						e.apply(void 0, t)
					}, this)
				}
			}),
			(t.EventEmitter.prototype.hasHandler = function (e) {
				return e in this.events
			}),
			(t.tokenizer = function (e) {
				if (!arguments.length || null === e || void 0 === e) return []
				if (Array.isArray(e)) {
					var n = e.filter(function (e) {
						return null === e || void 0 === e ? !1 : !0
					})
					n = n.map(function (e) {
						return t.utils.toString(e).toLowerCase()
					})
					var i = []
					return (
						n.forEach(function (e) {
							var n = e.split(t.tokenizer.seperator)
							i = i.concat(n)
						}, this),
						i
					)
				}
				return e.toString().trim().toLowerCase().split(t.tokenizer.seperator)
			}),
			(t.tokenizer.defaultSeperator = /[\s\-]+/),
			(t.tokenizer.seperator = t.tokenizer.defaultSeperator),
			(t.tokenizer.setSeperator = function (e) {
				null !== e &&
					void 0 !== e &&
					'object' == typeof e &&
					(t.tokenizer.seperator = e)
			}),
			(t.tokenizer.resetSeperator = function () {
				t.tokenizer.seperator = t.tokenizer.defaultSeperator
			}),
			(t.tokenizer.getSeperator = function () {
				return t.tokenizer.seperator
			}),
			(t.Pipeline = function () {
				this._queue = []
			}),
			(t.Pipeline.registeredFunctions = {}),
			(t.Pipeline.registerFunction = function (e, n) {
				n in t.Pipeline.registeredFunctions &&
					t.utils.warn('Overwriting existing registered function: ' + n),
					(e.label = n),
					(t.Pipeline.registeredFunctions[n] = e)
			}),
			(t.Pipeline.getRegisteredFunction = function (e) {
				return e in t.Pipeline.registeredFunctions != !0
					? null
					: t.Pipeline.registeredFunctions[e]
			}),
			(t.Pipeline.warnIfFunctionNotRegistered = function (e) {
				var n = e.label && e.label in this.registeredFunctions
				n ||
					t.utils.warn(
						'Function is not registered with pipeline. This may cause problems when serialising the index.\n',
						e
					)
			}),
			(t.Pipeline.load = function (e) {
				var n = new t.Pipeline()
				return (
					e.forEach(function (e) {
						var i = t.Pipeline.getRegisteredFunction(e)
						if (!i) throw new Error('Cannot load un-registered function: ' + e)
						n.add(i)
					}),
					n
				)
			}),
			(t.Pipeline.prototype.add = function () {
				var e = Array.prototype.slice.call(arguments)
				e.forEach(function (e) {
					t.Pipeline.warnIfFunctionNotRegistered(e), this._queue.push(e)
				}, this)
			}),
			(t.Pipeline.prototype.after = function (e, n) {
				t.Pipeline.warnIfFunctionNotRegistered(n)
				var i = this._queue.indexOf(e)
				if (-1 === i) throw new Error('Cannot find existingFn')
				this._queue.splice(i + 1, 0, n)
			}),
			(t.Pipeline.prototype.before = function (e, n) {
				t.Pipeline.warnIfFunctionNotRegistered(n)
				var i = this._queue.indexOf(e)
				if (-1 === i) throw new Error('Cannot find existingFn')
				this._queue.splice(i, 0, n)
			}),
			(t.Pipeline.prototype.remove = function (e) {
				var t = this._queue.indexOf(e)
				;-1 !== t && this._queue.splice(t, 1)
			}),
			(t.Pipeline.prototype.run = function (e) {
				for (
					var t = [], n = e.length, i = this._queue.length, o = 0;
					n > o;
					o++
				) {
					for (
						var r = e[o], s = 0;
						i > s &&
						((r = this._queue[s](r, o, e)), void 0 !== r && null !== r);
						s++
					);
					void 0 !== r && null !== r && t.push(r)
				}
				return t
			}),
			(t.Pipeline.prototype.reset = function () {
				this._queue = []
			}),
			(t.Pipeline.prototype.get = function () {
				return this._queue
			}),
			(t.Pipeline.prototype.toJSON = function () {
				return this._queue.map(function (e) {
					return t.Pipeline.warnIfFunctionNotRegistered(e), e.label
				})
			}),
			(t.Index = function () {
				;(this._fields = []),
					(this._ref = 'id'),
					(this.pipeline = new t.Pipeline()),
					(this.documentStore = new t.DocumentStore()),
					(this.index = {}),
					(this.eventEmitter = new t.EventEmitter()),
					(this._idfCache = {}),
					this.on(
						'add',
						'remove',
						'update',
						function () {
							this._idfCache = {}
						}.bind(this)
					)
			}),
			(t.Index.prototype.on = function () {
				var e = Array.prototype.slice.call(arguments)
				return this.eventEmitter.addListener.apply(this.eventEmitter, e)
			}),
			(t.Index.prototype.off = function (e, t) {
				return this.eventEmitter.removeListener(e, t)
			}),
			(t.Index.load = function (e) {
				e.version !== t.version &&
					t.utils.warn(
						'version mismatch: current ' + t.version + ' importing ' + e.version
					)
				var n = new this()
				;(n._fields = e.fields),
					(n._ref = e.ref),
					(n.documentStore = t.DocumentStore.load(e.documentStore)),
					(n.pipeline = t.Pipeline.load(e.pipeline)),
					(n.index = {})
				for (var i in e.index) n.index[i] = t.InvertedIndex.load(e.index[i])
				return n
			}),
			(t.Index.prototype.addField = function (e) {
				return (
					this._fields.push(e), (this.index[e] = new t.InvertedIndex()), this
				)
			}),
			(t.Index.prototype.setRef = function (e) {
				return (this._ref = e), this
			}),
			(t.Index.prototype.saveDocument = function (e) {
				return (this.documentStore = new t.DocumentStore(e)), this
			}),
			(t.Index.prototype.addDoc = function (e, n) {
				if (e) {
					var n = void 0 === n ? !0 : n,
						i = e[this._ref]
					this.documentStore.addDoc(i, e),
						this._fields.forEach(function (n) {
							var o = this.pipeline.run(t.tokenizer(e[n]))
							this.documentStore.addFieldLength(i, n, o.length)
							var r = {}
							o.forEach(function (e) {
								e in r ? (r[e] += 1) : (r[e] = 1)
							}, this)
							for (var s in r) {
								var u = r[s]
								;(u = Math.sqrt(u)),
									this.index[n].addToken(s, { ref: i, tf: u })
							}
						}, this),
						n && this.eventEmitter.emit('add', e, this)
				}
			}),
			(t.Index.prototype.removeDocByRef = function (e) {
				if (
					e &&
					this.documentStore.isDocStored() !== !1 &&
					this.documentStore.hasDoc(e)
				) {
					var t = this.documentStore.getDoc(e)
					this.removeDoc(t, !1)
				}
			}),
			(t.Index.prototype.removeDoc = function (e, n) {
				if (e) {
					var n = void 0 === n ? !0 : n,
						i = e[this._ref]
					this.documentStore.hasDoc(i) &&
						(this.documentStore.removeDoc(i),
						this._fields.forEach(function (n) {
							var o = this.pipeline.run(t.tokenizer(e[n]))
							o.forEach(function (e) {
								this.index[n].removeToken(e, i)
							}, this)
						}, this),
						n && this.eventEmitter.emit('remove', e, this))
				}
			}),
			(t.Index.prototype.updateDoc = function (e, t) {
				var t = void 0 === t ? !0 : t
				this.removeDocByRef(e[this._ref], !1),
					this.addDoc(e, !1),
					t && this.eventEmitter.emit('update', e, this)
			}),
			(t.Index.prototype.idf = function (e, t) {
				var n = '@' + t + '/' + e
				if (Object.prototype.hasOwnProperty.call(this._idfCache, n))
					return this._idfCache[n]
				var i = this.index[t].getDocFreq(e),
					o = 1 + Math.log(this.documentStore.length / (i + 1))
				return (this._idfCache[n] = o), o
			}),
			(t.Index.prototype.getFields = function () {
				return this._fields.slice()
			}),
			(t.Index.prototype.search = function (e, n) {
				if (!e) return []
				e = 'string' == typeof e ? { any: e } : JSON.parse(JSON.stringify(e))
				var i = null
				null != n && (i = JSON.stringify(n))
				for (
					var o = new t.Configuration(i, this.getFields()).get(),
						r = {},
						s = Object.keys(e),
						u = 0;
					u < s.length;
					u++
				) {
					var a = s[u]
					r[a] = this.pipeline.run(t.tokenizer(e[a]))
				}
				var l = {}
				for (var c in o) {
					var d = r[c] || r.any
					if (d) {
						var f = this.fieldSearch(d, c, o),
							h = o[c].boost
						for (var p in f) f[p] = f[p] * h
						for (var p in f) p in l ? (l[p] += f[p]) : (l[p] = f[p])
					}
				}
				var v,
					g = []
				for (var p in l)
					(v = { ref: p, score: l[p] }),
						this.documentStore.hasDoc(p) &&
							(v.doc = this.documentStore.getDoc(p)),
						g.push(v)
				return (
					g.sort(function (e, t) {
						return t.score - e.score
					}),
					g
				)
			}),
			(t.Index.prototype.fieldSearch = function (e, t, n) {
				var i = n[t].bool,
					o = n[t].expand,
					r = n[t].boost,
					s = null,
					u = {}
				return 0 !== r
					? (e.forEach(function (e) {
							var n = [e]
							1 == o && (n = this.index[t].expandToken(e))
							var r = {}
							n.forEach(function (n) {
								var o = this.index[t].getDocs(n),
									a = this.idf(n, t)
								if (s && 'AND' == i) {
									var l = {}
									for (var c in s) c in o && (l[c] = o[c])
									o = l
								}
								n == e && this.fieldSearchStats(u, n, o)
								for (var c in o) {
									var d = this.index[t].getTermFrequency(n, c),
										f = this.documentStore.getFieldLength(c, t),
										h = 1
									0 != f && (h = 1 / Math.sqrt(f))
									var p = 1
									n != e && (p = 0.15 * (1 - (n.length - e.length) / n.length))
									var v = d * a * h * p
									c in r ? (r[c] += v) : (r[c] = v)
								}
							}, this),
								(s = this.mergeScores(s, r, i))
					  }, this),
					  (s = this.coordNorm(s, u, e.length)))
					: void 0
			}),
			(t.Index.prototype.mergeScores = function (e, t, n) {
				if (!e) return t
				if ('AND' == n) {
					var i = {}
					for (var o in t) o in e && (i[o] = e[o] + t[o])
					return i
				}
				for (var o in t) o in e ? (e[o] += t[o]) : (e[o] = t[o])
				return e
			}),
			(t.Index.prototype.fieldSearchStats = function (e, t, n) {
				for (var i in n) i in e ? e[i].push(t) : (e[i] = [t])
			}),
			(t.Index.prototype.coordNorm = function (e, t, n) {
				for (var i in e)
					if (i in t) {
						var o = t[i].length
						e[i] = (e[i] * o) / n
					}
				return e
			}),
			(t.Index.prototype.toJSON = function () {
				var e = {}
				return (
					this._fields.forEach(function (t) {
						e[t] = this.index[t].toJSON()
					}, this),
					{
						version: t.version,
						fields: this._fields,
						ref: this._ref,
						documentStore: this.documentStore.toJSON(),
						index: e,
						pipeline: this.pipeline.toJSON(),
					}
				)
			}),
			(t.Index.prototype.use = function (e) {
				var t = Array.prototype.slice.call(arguments, 1)
				t.unshift(this), e.apply(this, t)
			}),
			(t.DocumentStore = function (e) {
				;(this._save = null === e || void 0 === e ? !0 : e),
					(this.docs = {}),
					(this.docInfo = {}),
					(this.length = 0)
			}),
			(t.DocumentStore.load = function (e) {
				var t = new this()
				return (
					(t.length = e.length),
					(t.docs = e.docs),
					(t.docInfo = e.docInfo),
					(t._save = e.save),
					t
				)
			}),
			(t.DocumentStore.prototype.isDocStored = function () {
				return this._save
			}),
			(t.DocumentStore.prototype.addDoc = function (t, n) {
				this.hasDoc(t) || this.length++,
					(this.docs[t] = this._save === !0 ? e(n) : null)
			}),
			(t.DocumentStore.prototype.getDoc = function (e) {
				return this.hasDoc(e) === !1 ? null : this.docs[e]
			}),
			(t.DocumentStore.prototype.hasDoc = function (e) {
				return e in this.docs
			}),
			(t.DocumentStore.prototype.removeDoc = function (e) {
				this.hasDoc(e) &&
					(delete this.docs[e], delete this.docInfo[e], this.length--)
			}),
			(t.DocumentStore.prototype.addFieldLength = function (e, t, n) {
				null !== e &&
					void 0 !== e &&
					0 != this.hasDoc(e) &&
					(this.docInfo[e] || (this.docInfo[e] = {}), (this.docInfo[e][t] = n))
			}),
			(t.DocumentStore.prototype.updateFieldLength = function (e, t, n) {
				null !== e &&
					void 0 !== e &&
					0 != this.hasDoc(e) &&
					this.addFieldLength(e, t, n)
			}),
			(t.DocumentStore.prototype.getFieldLength = function (e, t) {
				return null === e || void 0 === e
					? 0
					: e in this.docs && t in this.docInfo[e]
					? this.docInfo[e][t]
					: 0
			}),
			(t.DocumentStore.prototype.toJSON = function () {
				return {
					docs: this.docs,
					docInfo: this.docInfo,
					length: this.length,
					save: this._save,
				}
			}),
			(t.stemmer = (function () {
				var e = {
						ational: 'ate',
						tional: 'tion',
						enci: 'ence',
						anci: 'ance',
						izer: 'ize',
						bli: 'ble',
						alli: 'al',
						entli: 'ent',
						eli: 'e',
						ousli: 'ous',
						ization: 'ize',
						ation: 'ate',
						ator: 'ate',
						alism: 'al',
						iveness: 'ive',
						fulness: 'ful',
						ousness: 'ous',
						aliti: 'al',
						iviti: 'ive',
						biliti: 'ble',
						logi: 'log',
					},
					t = {
						icate: 'ic',
						ative: '',
						alize: 'al',
						iciti: 'ic',
						ical: 'ic',
						ful: '',
						ness: '',
					},
					n = '[^aeiou]',
					i = '[aeiouy]',
					o = n + '[^aeiouy]*',
					r = i + '[aeiou]*',
					s = '^(' + o + ')?' + r + o,
					u = '^(' + o + ')?' + r + o + '(' + r + ')?$',
					a = '^(' + o + ')?' + r + o + r + o,
					l = '^(' + o + ')?' + i,
					c = new RegExp(s),
					d = new RegExp(a),
					f = new RegExp(u),
					h = new RegExp(l),
					p = /^(.+?)(ss|i)es$/,
					v = /^(.+?)([^s])s$/,
					g = /^(.+?)eed$/,
					m = /^(.+?)(ed|ing)$/,
					y = /.$/,
					S = /(at|bl|iz)$/,
					x = new RegExp('([^aeiouylsz])\\1$'),
					w = new RegExp('^' + o + i + '[^aeiouwxy]$'),
					I = /^(.+?[^aeiou])y$/,
					b =
						/^(.+?)(ational|tional|enci|anci|izer|bli|alli|entli|eli|ousli|ization|ation|ator|alism|iveness|fulness|ousness|aliti|iviti|biliti|logi)$/,
					E = /^(.+?)(icate|ative|alize|iciti|ical|ful|ness)$/,
					D =
						/^(.+?)(al|ance|ence|er|ic|able|ible|ant|ement|ment|ent|ou|ism|ate|iti|ous|ive|ize)$/,
					F = /^(.+?)(s|t)(ion)$/,
					_ = /^(.+?)e$/,
					P = /ll$/,
					k = new RegExp('^' + o + i + '[^aeiouwxy]$'),
					z = function (n) {
						var i, o, r, s, u, a, l
						if (n.length < 3) return n
						if (
							((r = n.substr(0, 1)),
							'y' == r && (n = r.toUpperCase() + n.substr(1)),
							(s = p),
							(u = v),
							s.test(n)
								? (n = n.replace(s, '$1$2'))
								: u.test(n) && (n = n.replace(u, '$1$2')),
							(s = g),
							(u = m),
							s.test(n))
						) {
							var z = s.exec(n)
							;(s = c), s.test(z[1]) && ((s = y), (n = n.replace(s, '')))
						} else if (u.test(n)) {
							var z = u.exec(n)
							;(i = z[1]),
								(u = h),
								u.test(i) &&
									((n = i),
									(u = S),
									(a = x),
									(l = w),
									u.test(n)
										? (n += 'e')
										: a.test(n)
										? ((s = y), (n = n.replace(s, '')))
										: l.test(n) && (n += 'e'))
						}
						if (((s = I), s.test(n))) {
							var z = s.exec(n)
							;(i = z[1]), (n = i + 'i')
						}
						if (((s = b), s.test(n))) {
							var z = s.exec(n)
							;(i = z[1]), (o = z[2]), (s = c), s.test(i) && (n = i + e[o])
						}
						if (((s = E), s.test(n))) {
							var z = s.exec(n)
							;(i = z[1]), (o = z[2]), (s = c), s.test(i) && (n = i + t[o])
						}
						if (((s = D), (u = F), s.test(n))) {
							var z = s.exec(n)
							;(i = z[1]), (s = d), s.test(i) && (n = i)
						} else if (u.test(n)) {
							var z = u.exec(n)
							;(i = z[1] + z[2]), (u = d), u.test(i) && (n = i)
						}
						if (((s = _), s.test(n))) {
							var z = s.exec(n)
							;(i = z[1]),
								(s = d),
								(u = f),
								(a = k),
								(s.test(i) || (u.test(i) && !a.test(i))) && (n = i)
						}
						return (
							(s = P),
							(u = d),
							s.test(n) && u.test(n) && ((s = y), (n = n.replace(s, ''))),
							'y' == r && (n = r.toLowerCase() + n.substr(1)),
							n
						)
					}
				return z
			})()),
			t.Pipeline.registerFunction(t.stemmer, 'stemmer'),
			(t.stopWordFilter = function (e) {
				return e && t.stopWordFilter.stopWords[e] !== !0 ? e : void 0
			}),
			(t.clearStopWords = function () {
				t.stopWordFilter.stopWords = {}
			}),
			(t.addStopWords = function (e) {
				null != e &&
					Array.isArray(e) !== !1 &&
					e.forEach(function (e) {
						t.stopWordFilter.stopWords[e] = !0
					}, this)
			}),
			(t.resetStopWords = function () {
				t.stopWordFilter.stopWords = t.defaultStopWords
			}),
			(t.defaultStopWords = {
				'': !0,
				a: !0,
				able: !0,
				about: !0,
				across: !0,
				after: !0,
				all: !0,
				almost: !0,
				also: !0,
				am: !0,
				among: !0,
				an: !0,
				and: !0,
				any: !0,
				are: !0,
				as: !0,
				at: !0,
				be: !0,
				because: !0,
				been: !0,
				but: !0,
				by: !0,
				can: !0,
				cannot: !0,
				could: !0,
				dear: !0,
				did: !0,
				do: !0,
				does: !0,
				either: !0,
				else: !0,
				ever: !0,
				every: !0,
				for: !0,
				from: !0,
				get: !0,
				got: !0,
				had: !0,
				has: !0,
				have: !0,
				he: !0,
				her: !0,
				hers: !0,
				him: !0,
				his: !0,
				how: !0,
				however: !0,
				i: !0,
				if: !0,
				in: !0,
				into: !0,
				is: !0,
				it: !0,
				its: !0,
				just: !0,
				least: !0,
				let: !0,
				like: !0,
				likely: !0,
				may: !0,
				me: !0,
				might: !0,
				most: !0,
				must: !0,
				my: !0,
				neither: !0,
				no: !0,
				nor: !0,
				not: !0,
				of: !0,
				off: !0,
				often: !0,
				on: !0,
				only: !0,
				or: !0,
				other: !0,
				our: !0,
				own: !0,
				rather: !0,
				said: !0,
				say: !0,
				says: !0,
				she: !0,
				should: !0,
				since: !0,
				so: !0,
				some: !0,
				than: !0,
				that: !0,
				the: !0,
				their: !0,
				them: !0,
				then: !0,
				there: !0,
				these: !0,
				they: !0,
				this: !0,
				tis: !0,
				to: !0,
				too: !0,
				twas: !0,
				us: !0,
				wants: !0,
				was: !0,
				we: !0,
				were: !0,
				what: !0,
				when: !0,
				where: !0,
				which: !0,
				while: !0,
				who: !0,
				whom: !0,
				why: !0,
				will: !0,
				with: !0,
				would: !0,
				yet: !0,
				you: !0,
				your: !0,
			}),
			(t.stopWordFilter.stopWords = t.defaultStopWords),
			t.Pipeline.registerFunction(t.stopWordFilter, 'stopWordFilter'),
			(t.trimmer = function (e) {
				if (null === e || void 0 === e)
					throw new Error('token should not be undefined')
				return e.replace(/^\W+/, '').replace(/\W+$/, '')
			}),
			t.Pipeline.registerFunction(t.trimmer, 'trimmer'),
			(t.InvertedIndex = function () {
				this.root = { docs: {}, df: 0 }
			}),
			(t.InvertedIndex.load = function (e) {
				var t = new this()
				return (t.root = e.root), t
			}),
			(t.InvertedIndex.prototype.addToken = function (e, t, n) {
				for (var n = n || this.root, i = 0; i <= e.length - 1; ) {
					var o = e[i]
					o in n || (n[o] = { docs: {}, df: 0 }), (i += 1), (n = n[o])
				}
				var r = t.ref
				n.docs[r]
					? (n.docs[r] = { tf: t.tf })
					: ((n.docs[r] = { tf: t.tf }), (n.df += 1))
			}),
			(t.InvertedIndex.prototype.hasToken = function (e) {
				if (!e) return !1
				for (var t = this.root, n = 0; n < e.length; n++) {
					if (!t[e[n]]) return !1
					t = t[e[n]]
				}
				return !0
			}),
			(t.InvertedIndex.prototype.getNode = function (e) {
				if (!e) return null
				for (var t = this.root, n = 0; n < e.length; n++) {
					if (!t[e[n]]) return null
					t = t[e[n]]
				}
				return t
			}),
			(t.InvertedIndex.prototype.getDocs = function (e) {
				var t = this.getNode(e)
				return null == t ? {} : t.docs
			}),
			(t.InvertedIndex.prototype.getTermFrequency = function (e, t) {
				var n = this.getNode(e)
				return null == n ? 0 : t in n.docs ? n.docs[t].tf : 0
			}),
			(t.InvertedIndex.prototype.getDocFreq = function (e) {
				var t = this.getNode(e)
				return null == t ? 0 : t.df
			}),
			(t.InvertedIndex.prototype.removeToken = function (e, t) {
				if (e) {
					var n = this.getNode(e)
					null != n && t in n.docs && (delete n.docs[t], (n.df -= 1))
				}
			}),
			(t.InvertedIndex.prototype.expandToken = function (e, t, n) {
				if (null == e || '' == e) return []
				var t = t || []
				if (void 0 == n && ((n = this.getNode(e)), null == n)) return t
				n.df > 0 && t.push(e)
				for (var i in n)
					'docs' !== i && 'df' !== i && this.expandToken(e + i, t, n[i])
				return t
			}),
			(t.InvertedIndex.prototype.toJSON = function () {
				return { root: this.root }
			}),
			(t.Configuration = function (e, n) {
				var e = e || ''
				if (void 0 == n || null == n)
					throw new Error('fields should not be null')
				this.config = {}
				var i
				try {
					;(i = JSON.parse(e)), this.buildUserConfig(i, n)
				} catch (o) {
					t.utils.warn(
						'user configuration parse failed, will use default configuration'
					),
						this.buildDefaultConfig(n)
				}
			}),
			(t.Configuration.prototype.buildDefaultConfig = function (e) {
				this.reset(),
					e.forEach(function (e) {
						this.config[e] = { boost: 1, bool: 'OR', expand: !1 }
					}, this)
			}),
			(t.Configuration.prototype.buildUserConfig = function (e, n) {
				var i = 'OR',
					o = !1
				if (
					(this.reset(),
					'bool' in e && (i = e.bool || i),
					'expand' in e && (o = e.expand || o),
					'fields' in e)
				)
					for (var r in e.fields)
						if (n.indexOf(r) > -1) {
							var s = e.fields[r],
								u = o
							void 0 != s.expand && (u = s.expand),
								(this.config[r] = {
									boost: s.boost || 0 === s.boost ? s.boost : 1,
									bool: s.bool || i,
									expand: u,
								})
						} else
							t.utils.warn(
								'field name in user configuration not found in index instance fields'
							)
				else this.addAllFields2UserConfig(i, o, n)
			}),
			(t.Configuration.prototype.addAllFields2UserConfig = function (e, t, n) {
				n.forEach(function (n) {
					this.config[n] = { boost: 1, bool: e, expand: t }
				}, this)
			}),
			(t.Configuration.prototype.get = function () {
				return this.config
			}),
			(t.Configuration.prototype.reset = function () {
				this.config = {}
			}),
			(lunr.SortedSet = function () {
				;(this.length = 0), (this.elements = [])
			}),
			(lunr.SortedSet.load = function (e) {
				var t = new this()
				return (t.elements = e), (t.length = e.length), t
			}),
			(lunr.SortedSet.prototype.add = function () {
				var e, t
				for (e = 0; e < arguments.length; e++)
					(t = arguments[e]),
						~this.indexOf(t) || this.elements.splice(this.locationFor(t), 0, t)
				this.length = this.elements.length
			}),
			(lunr.SortedSet.prototype.toArray = function () {
				return this.elements.slice()
			}),
			(lunr.SortedSet.prototype.map = function (e, t) {
				return this.elements.map(e, t)
			}),
			(lunr.SortedSet.prototype.forEach = function (e, t) {
				return this.elements.forEach(e, t)
			}),
			(lunr.SortedSet.prototype.indexOf = function (e) {
				for (
					var t = 0,
						n = this.elements.length,
						i = n - t,
						o = t + Math.floor(i / 2),
						r = this.elements[o];
					i > 1;

				) {
					if (r === e) return o
					e > r && (t = o),
						r > e && (n = o),
						(i = n - t),
						(o = t + Math.floor(i / 2)),
						(r = this.elements[o])
				}
				return r === e ? o : -1
			}),
			(lunr.SortedSet.prototype.locationFor = function (e) {
				for (
					var t = 0,
						n = this.elements.length,
						i = n - t,
						o = t + Math.floor(i / 2),
						r = this.elements[o];
					i > 1;

				)
					e > r && (t = o),
						r > e && (n = o),
						(i = n - t),
						(o = t + Math.floor(i / 2)),
						(r = this.elements[o])
				return r > e ? o : e > r ? o + 1 : void 0
			}),
			(lunr.SortedSet.prototype.intersect = function (e) {
				for (
					var t = new lunr.SortedSet(),
						n = 0,
						i = 0,
						o = this.length,
						r = e.length,
						s = this.elements,
						u = e.elements;
					;

				) {
					if (n > o - 1 || i > r - 1) break
					s[n] !== u[i]
						? s[n] < u[i]
							? n++
							: s[n] > u[i] && i++
						: (t.add(s[n]), n++, i++)
				}
				return t
			}),
			(lunr.SortedSet.prototype.clone = function () {
				var e = new lunr.SortedSet()
				return (e.elements = this.toArray()), (e.length = e.elements.length), e
			}),
			(lunr.SortedSet.prototype.union = function (e) {
				var t, n, i
				this.length >= e.length ? ((t = this), (n = e)) : ((t = e), (n = this)),
					(i = t.clone())
				for (var o = 0, r = n.toArray(); o < r.length; o++) i.add(r[o])
				return i
			}),
			(lunr.SortedSet.prototype.toJSON = function () {
				return this.toArray()
			}),
			(function (e, t) {
				'function' == typeof define && define.amd
					? define(t)
					: 'object' == typeof exports
					? (module.exports = t())
					: (e.elasticlunr = t())
			})(this, function () {
				return t
			})
	})()
	/** pdoc search index */ const docs = [
		{
			fullname: 'ddii_scopus',
			modulename: 'ddii_scopus',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.MainUIRenderer',
			modulename: 'ddii_scopus.MainUIRenderer',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.main',
			modulename: 'ddii_scopus.main',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules',
			modulename: 'ddii_scopus.modules',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Emulator',
			modulename: 'ddii_scopus.modules.Emulator',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Emulator.emulator',
			modulename: 'ddii_scopus.modules.Emulator.emulator',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.MainUIRenderer',
			modulename: 'ddii_scopus.modules.MainUIRenderer',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.src_path',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'src_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: 'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.modules_path',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'modules_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value:
				'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus/modules&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.MainUIRenderer',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'MainUIRenderer',
			kind: 'class',
			doc: '<p>QMainWindow(parent: Optional[QWidget] = None, flags: Qt.WindowType = Qt.WindowFlags())</p>\n',
			bases: 'PyQt6.QtWidgets.QMainWindow',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.MainUIRenderer.gridLayout_main_split',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'MainUIRenderer.gridLayout_main_split',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QGridLayout',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.MainUIRenderer.coroutine_get_client_finished',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'MainUIRenderer.coroutine_get_client_finished',
			kind: 'function',
			doc: "<p>pyqtSignal(*types, name: str = ..., revision: int = ..., arguments: Sequence = ...) -> PYQT_SIGNAL</p>\n\n<p>types is normally a sequence of individual types.  Each type is either a\ntype object or a string that is the name of a C++ type.  Alternatively\neach type could itself be a sequence of types each describing a different\noverloaded signal.\nname is the optional C++ name of the signal.  If it is not specified then\nthe name of the class attribute that is bound to the signal is used.\nrevision is the optional revision of the signal that is exported to QML.\nIf it is not specified then 0 is used.\narguments is the optional sequence of the names of the signal's arguments.</p>\n",
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">unknown</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.MainUIRenderer.mw',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'MainUIRenderer.mw',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': src.modbus_worker.ModbusWorker',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.MainUIRenderer.parser',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'MainUIRenderer.parser',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': src.parsers.Parsers',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.MainUIRenderer.logger',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'MainUIRenderer.logger',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.MainUIRenderer.widget_model',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'MainUIRenderer.widget_model',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.MainUIRenderer.on_tab_widget_handler',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'MainUIRenderer.on_tab_widget_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">index</span><span class="p">:</span> <span class="nb">int</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.MainUIRenderer.MainUIRenderer.MainUIRenderer.init_widgets',
			modulename: 'ddii_scopus.modules.MainUIRenderer.MainUIRenderer',
			qualname: 'MainUIRenderer.init_widgets',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.modules.MainUIRenderer.scopus',
			modulename: 'ddii_scopus.modules.MainUIRenderer.scopus',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Config',
			modulename: 'ddii_scopus.modules.Main_Config',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Config.main_config_dialog.src_path',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'src_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: 'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.modules_path',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'modules_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value:
				'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus/modules&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog',
			kind: 'class',
			doc: '<p>QDialog(parent: Optional[QWidget] = None, flags: Qt.WindowType = Qt.WindowFlags())</p>\n',
			bases: 'PyQt6.QtWidgets.QDialog, src.env_var.EnvironmentVar',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.__init__',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">logger</span>, </span><span class="param"><span class="o">*</span><span class="n">args</span></span>)</span>',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_interval',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_interval',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_hvip_pips',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_hvip_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_hvip_sipm',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_hvip_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_hvip_ch',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_hvip_ch',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_pwm_sipm',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_pwm_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_pwm_pips',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_pwm_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_pwm_ch',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_pwm_ch',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_pwm_max_sipm',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_pwm_max_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_pwm_max_pips',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_pwm_max_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_pwm_max_ch',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_pwm_max_ch',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_lvl_0_1',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_lvl_0_1',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_lvl_0_5',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_lvl_0_5',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_lvl_0_8',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_lvl_0_8',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_lvl_1_6',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_lvl_1_6',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_lvl_3',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_lvl_3',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_lvl_5',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_lvl_5',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_lvl_10',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_lvl_10',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_lvl_30',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_lvl_30',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_lvl_60',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_lvl_60',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.label_check_cfg',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.label_check_cfg',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.pushButton_save_hvip',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.pushButton_save_hvip',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.pushButton_save_mpp',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.pushButton_save_mpp',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.lineEdit_cfg_mpp_id',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.lineEdit_cfg_mpp_id',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.vLayout_ser_connect',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.vLayout_ser_connect',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QVBoxLayout',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.radioButton_mpp',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.radioButton_mpp',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QRadioButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.radioButton_cm',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.radioButton_cm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QRadioButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.pushButton_Get_Rst',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.pushButton_Get_Rst',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.CM_DBG_SET_CFG',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.CM_DBG_SET_CFG',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '5',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.CM_ID',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.CM_ID',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '1',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.mw',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.mw',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.parser',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.parser',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.logger',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.logger',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.config',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.config',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.flg_get_rst',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.flg_get_rst',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.update_pack_from_widget',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.update_pack_from_widget',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.init_linEdit_list',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.init_linEdit_list',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">tuple</span><span class="p">[</span><span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QLineEdit</span><span class="p">],</span> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QLineEdit</span><span class="p">]]</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.get_client',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.get_client',
			kind: 'function',
			doc: '<p>\u0424\u0443\u043d\u043a\u0446\u0438\u044f \u043f\u0435\u0440\u0435\u0445\u0432\u0430\u0442\u044b\u0432\u0430\u0435\u0442 client \u0438 \u043f\u0435\u0440\u0435\u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0430\u0435\u0442\u0441\u044f \u043a \u043d\u0435\u043c\u0443</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.update_gui_data_mpp',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.update_gui_data_mpp',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.update_gui_data_cm',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.update_gui_data_cm',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.closeEvent',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.closeEvent',
			kind: 'function',
			doc: '<p>closeEvent(self, a0: Optional[QCloseEvent])</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">event</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.pushButton_save_cfg_handler',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.pushButton_save_cfg_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.check_writed_cfg',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.check_writed_cfg',
			kind: 'function',
			doc: '<p>\u041f\u043e\u0432\u0435\u0440\u044f\u0435\u0442 \u0437\u0430\u043f\u0438\u0441\u0430\u043b\u0430\u0441\u044c \u043b\u0438 \u0432 \u043f\u0430\u043c\u044f\u0442\u044c \u043a\u043e\u043d\u0444\u0438\u0433\u0443\u0440\u0430\u0446\u0438\u044f\nArgs:\n    data (list[int]): \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435 \u043a\u043e\u043d\u0446\u0438\u0433\u0443\u0440\u0430\u0446\u0438\u0438\n    device (str): \n    - "cm"\n    - "mpp"\nReturns:\n    bool: \u0421\u0442\u0430\u0442\u0443\u0441 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span>, </span><span class="param"><span class="n">device</span><span class="p">:</span> <span class="nb">str</span></span><span class="return-annotation">) -> <span class="nb">bool</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.pushButton_get_rst_handler',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.pushButton_get_rst_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.get_cfg_data_from_widget',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.get_cfg_data_from_widget',
			kind: 'function',
			doc: '<p>\u041f\u043e\u043b\u0443\u0447\u0430\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0435 \u0441 \u0432\u0438\u0434\u0436\u0435\u0442\u043e\u0432 \u0438 \u0443\u043f\u0430\u043a\u043e\u0432\u044b\u0432\u0430\u0435\u0442 \u0438\u0445 \u0432 \u043f\u0430\u043a\u0435\u0442\nArgs:\n    device (str): \u0423\u043a\u0430\u0437\u0430\u0442\u044c \u043c\u043e\u0434\u0443\u043b\u044c:\n    - "cm"\n    - "mpp"\nReturns:\n    list[int]: \u041f\u0430\u043a\u0435\u0442 \u0434\u043b\u044f \u043e\u0442\u043f\u0440\u0430\u0432\u043a\u0438 \u043f\u043e \u0412\u0428</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">device</span><span class="p">:</span> <span class="nb">str</span></span><span class="return-annotation">) -> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.main_config_dialog.MainConfigDialog.initValidator',
			modulename: 'ddii_scopus.modules.Main_Config.main_config_dialog',
			qualname: 'MainConfigDialog.initValidator',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">validator</span>, </span><span class="param"><span class="n">d_validator</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Config.save_config',
			modulename: 'ddii_scopus.modules.Main_Config.save_config',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Config.save_config.settings',
			modulename: 'ddii_scopus.modules.Main_Config.save_config',
			qualname: 'settings',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '&lt;dynaconf.base.LazySettings object&gt;',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Config.save_config.ConfigSaver',
			modulename: 'ddii_scopus.modules.Main_Config.save_config',
			qualname: 'ConfigSaver',
			kind: 'class',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.save_config.ConfigSaver.__init__',
			modulename: 'ddii_scopus.modules.Main_Config.save_config',
			qualname: 'ConfigSaver.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="o">*</span><span class="n">args</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Config.save_config.ConfigSaver.wd',
			modulename: 'ddii_scopus.modules.Main_Config.save_config',
			qualname: 'ConfigSaver.wd',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.save_config.ConfigSaver.save_to_config',
			modulename: 'ddii_scopus.modules.Main_Config.save_config',
			qualname: 'ConfigSaver.save_to_config',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Config.save_config.ConfigSaver.load_from_config',
			modulename: 'ddii_scopus.modules.Main_Config.save_config',
			qualname: 'ConfigSaver.load_from_config',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Graph_Widget',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.src_path',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'src_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: 'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.modules_path',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'modules_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value:
				'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus/modules&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.widgets_path',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'widgets_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value:
				'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus/modules/Main_Graph_Widget/MainUIRenderer/widgets&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget',
			kind: 'class',
			doc: '<p>QDialog(parent: Optional[QWidget] = None, flags: Qt.WindowType = Qt.WindowFlags())</p>\n',
			bases: 'PyQt6.QtWidgets.QDialog',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.__init__',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">logger</span>, </span><span class="param"><span class="o">*</span><span class="n">args</span></span>)</span>',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.lineEdit_T_cher',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.lineEdit_T_cher',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.lineEdit_T_sipm',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.lineEdit_T_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.pushButton_OK',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.pushButton_OK',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.vLayout_ser_connect',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.vLayout_ser_connect',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QVBoxLayout',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.verticalLayout_graph',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.verticalLayout_graph',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QVBoxLayout',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.coroutine_get_temp_finished',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.coroutine_get_temp_finished',
			kind: 'function',
			doc: "<p>pyqtSignal(*types, name: str = ..., revision: int = ..., arguments: Sequence = ...) -> PYQT_SIGNAL</p>\n\n<p>types is normally a sequence of individual types.  Each type is either a\ntype object or a string that is the name of a C++ type.  Alternatively\neach type could itself be a sequence of types each describing a different\noverloaded signal.\nname is the optional C++ name of the signal.  If it is not specified then\nthe name of the class attribute that is bound to the signal is used.\nrevision is the optional revision of the signal that is exported to QML.\nIf it is not specified then 0 is used.\narguments is the optional sequence of the names of the signal's arguments.</p>\n",
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">unknown</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.mw',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.mw',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.parser',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.parser',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.logger',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.logger',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.flg_get_rst',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.flg_get_rst',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.task',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.task',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget.MainGraphWidget.get_client',
			modulename: 'ddii_scopus.modules.Main_Graph_Widget.main_graph_widget',
			qualname: 'MainGraphWidget.get_client',
			kind: 'function',
			doc: '<p>\u041f\u0435\u0440\u0435\u0445\u0432\u0430\u0442\u044b\u0432\u0430\u0435\u0442 client \u043e\u0442 SerialConnect \u0438 \u043f\u0435\u0440\u0435\u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0430\u0435\u0442\u0441\u044f \u043a \u043d\u0435\u043c\u0443</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Hvip',
			modulename: 'ddii_scopus.modules.Main_Hvip',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.src_path',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'src_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: 'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus&#x27;)',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.modules_path',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'modules_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value:
				'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus/modules&#x27;)',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog',
			kind: 'class',
			doc: '<p>QDialog(parent: Optional[QWidget] = None, flags: Qt.WindowType = Qt.WindowFlags())</p>\n',
			bases: 'PyQt6.QtWidgets.QDialog',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.__init__',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">logger</span>, </span><span class="param"><span class="o">*</span><span class="n">args</span></span>)</span>',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_ch_volt',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_ch_volt',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_pips_volt',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_pips_volt',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_sipm_volt',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_sipm_volt',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.doubleSpinBox_ch_pwm',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.doubleSpinBox_ch_pwm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.doubleSpinBox_pips_pwm',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.doubleSpinBox_pips_pwm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.doubleSpinBox_sipm_pwm',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.doubleSpinBox_sipm_pwm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_ch_cur',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_ch_cur',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_sipm_cur',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_sipm_cur',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_pips_cur',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_pips_cur',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_ch_pwm_mes',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_ch_pwm_mes',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_pips_pwm_mes',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_pips_pwm_mes',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_sipm_pwm_mes',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_sipm_pwm_mes',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_ch_v_mes',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_ch_v_mes',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_pips_v_mes',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_pips_v_mes',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_sipm_v_mes',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_sipm_v_mes',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_status',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_status',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_ch_a_u',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_ch_a_u',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_ch_b_u',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_ch_b_u',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_ch_a_i',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_ch_a_i',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_ch_b_i',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_ch_b_i',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_pips_a_u',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_pips_a_u',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_pips_b_u',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_pips_b_u',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_pips_a_i',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_pips_a_i',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_pips_b_i',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_pips_b_i',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_sipm_a_u',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_sipm_a_u',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_sipm_b_u',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_sipm_b_u',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_sipm_a_i',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_sipm_a_i',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.spinBox_sipm_b_i',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.spinBox_sipm_b_i',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QDoubleSpinBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_ok',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_ok',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_apply',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_apply',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_pips_on',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_pips_on',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_sipm_on',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_sipm_on',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_ch_on',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_ch_on',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_get_rst',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_get_rst',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.led_pips',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.led_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QWidget',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.led_sipm',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.led_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QWidget',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.led_ch',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.led_ch',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QWidget',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_desired_v_pips',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_desired_v_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_desired_v_sipm',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_desired_v_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.label_desired_v_ch',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.label_desired_v_ch',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.vLayout_ser_connect',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.vLayout_ser_connect',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QVBoxLayout',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.PIPS_CH_VOLTAGE',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.PIPS_CH_VOLTAGE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '1',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.SIPM_CH_VOLTAGE',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.SIPM_CH_VOLTAGE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '2',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.CHERENKOV_CH_VOLTAGE',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.CHERENKOV_CH_VOLTAGE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '3',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.coroutine_get_client_finished',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.coroutine_get_client_finished',
			kind: 'function',
			doc: "<p>pyqtSignal(*types, name: str = ..., revision: int = ..., arguments: Sequence = ...) -> PYQT_SIGNAL</p>\n\n<p>types is normally a sequence of individual types.  Each type is either a\ntype object or a string that is the name of a C++ type.  Alternatively\neach type could itself be a sequence of types each describing a different\noverloaded signal.\nname is the optional C++ name of the signal.  If it is not specified then\nthe name of the class attribute that is bound to the signal is used.\nrevision is the optional revision of the signal that is exported to QML.\nIf it is not specified then 0 is used.\narguments is the optional sequence of the names of the signal's arguments.</p>\n",
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">unknown</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.mw',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.mw',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.parser',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.parser',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.logger',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.logger',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.config',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.config',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.flg_get_rst',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.flg_get_rst',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.task',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.task',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.flag_measure',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.flag_measure',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.get_client',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.get_client',
			kind: 'function',
			doc: '<p>\u041f\u0435\u0440\u0435\u0445\u0432\u0430\u0442\u044b\u0432\u0430\u0435\u0442 client \u043e\u0442 SerialConnect \u0438 \u043f\u0435\u0440\u0435\u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0430\u0435\u0442\u0441\u044f \u043a \u043d\u0435\u043c\u0443</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.creator_task',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.creator_task',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.init_QObjects',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.init_QObjects',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.asyncio_loop_request',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.asyncio_loop_request',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.get_cfg_data_from_widget',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.get_cfg_data_from_widget',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">d_struct</span><span class="p">:</span> <span class="nb">dict</span>, </span><span class="param"><span class="n">tp</span><span class="p">:</span> <span class="nb">str</span></span><span class="return-annotation">) -> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.update_gui_data_spinbox',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.update_gui_data_spinbox',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.update_gui_data_label',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.update_gui_data_label',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_pips_on_handler',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_pips_on_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_sipm_on_handler',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_sipm_on_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_ch_on_handler',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_ch_on_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_apply_handler',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_apply_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.save_gui_data',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.save_gui_data',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_get_rst_handler',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_get_rst_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.pushButton_ok_handler',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.pushButton_ok_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.update_power_status',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.update_power_status',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.main_hvip_dialog.MainHvipDialog.closeEvent',
			modulename: 'ddii_scopus.modules.Main_Hvip.main_hvip_dialog',
			qualname: 'MainHvipDialog.closeEvent',
			kind: 'function',
			doc: '<p>closeEvent(self, a0: Optional[QCloseEvent])</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">event</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Hvip.save_config',
			modulename: 'ddii_scopus.modules.Main_Hvip.save_config',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Hvip.save_config.settings',
			modulename: 'ddii_scopus.modules.Main_Hvip.save_config',
			qualname: 'settings',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '&lt;dynaconf.base.LazySettings object&gt;',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Hvip.save_config.ConfigSaver',
			modulename: 'ddii_scopus.modules.Main_Hvip.save_config',
			qualname: 'ConfigSaver',
			kind: 'class',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.save_config.ConfigSaver.save_to_config',
			modulename: 'ddii_scopus.modules.Main_Hvip.save_config',
			qualname: 'ConfigSaver.save_to_config',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">wd_dict</span><span class="p">:</span> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">float</span> <span class="o">|</span> <span class="nb">int</span> <span class="o">|</span> <span class="nb">str</span><span class="p">]</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Hvip.save_config.ConfigSaver.load_from_config',
			modulename: 'ddii_scopus.modules.Main_Hvip.save_config',
			qualname: 'ConfigSaver.load_from_config',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">wd_dict</span><span class="p">:</span> <span class="nb">dict</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Serial',
			modulename: 'ddii_scopus.modules.Main_Serial',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Serial.QLineEdit_custom_resize',
			modulename: 'ddii_scopus.modules.Main_Serial.QLineEdit_custom_resize',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.QLineEdit_custom_resize.AutoSizeLineEdit',
			modulename: 'ddii_scopus.modules.Main_Serial.QLineEdit_custom_resize',
			qualname: 'AutoSizeLineEdit',
			kind: 'class',
			doc: '<p>QLineEdit(parent: Optional[QWidget] = None)\nQLineEdit(contents: Optional[str], parent: Optional[QWidget] = None)</p>\n',
			bases: 'PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.QLineEdit_custom_resize.AutoSizeLineEdit.__init__',
			modulename: 'ddii_scopus.modules.Main_Serial.QLineEdit_custom_resize',
			qualname: 'AutoSizeLineEdit.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">parent</span><span class="o">=</span><span class="kc">None</span></span>)</span>',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.QLineEdit_custom_resize.AutoSizeLineEdit.adjust_size',
			modulename: 'ddii_scopus.modules.Main_Serial.QLineEdit_custom_resize',
			qualname: 'AutoSizeLineEdit.adjust_size',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Serial.main_serial_dialog.src_path',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'src_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: 'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.modules_path',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'modules_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value:
				'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus/modules&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect',
			kind: 'class',
			doc: '<p>QWidget(parent: Optional[QWidget] = None, flags: Qt.WindowType = Qt.WindowFlags())</p>\n',
			bases: 'PyQt6.QtWidgets.QWidget, src.env_var.EnvironmentVar',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.__init__',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">logger</span>, </span><span class="param"><span class="o">**</span><span class="n">kwargs</span></span>)</span>',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.pushButton_connect_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.pushButton_connect_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.lineEdit_Bauderate_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.lineEdit_Bauderate_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.lineEdit_ID_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.lineEdit_ID_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.widget_led_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.widget_led_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QWidget',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.label_state_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.label_state_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.horizontalLayout_comport',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.horizontalLayout_comport',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QHBoxLayout',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.coroutine_finished',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.coroutine_finished',
			kind: 'function',
			doc: "<p>pyqtSignal(*types, name: str = ..., revision: int = ..., arguments: Sequence = ...) -> PYQT_SIGNAL</p>\n\n<p>types is normally a sequence of individual types.  Each type is either a\ntype object or a string that is the name of a C++ type.  Alternatively\neach type could itself be a sequence of types each describing a different\noverloaded signal.\nname is the optional C++ name of the signal.  If it is not specified then\nthe name of the class attribute that is bound to the signal is used.\nrevision is the optional revision of the signal that is exported to QML.\nIf it is not specified then 0 is used.\narguments is the optional sequence of the names of the signal's arguments.</p>\n",
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">unknown</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.mw',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.mw',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.logger',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.logger',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.comboBox_comm',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.comboBox_comm',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.size_policy',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.size_policy',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QSizePolicy',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.pushButton_connect_flag',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.pushButton_connect_flag',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.mpp_id',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.mpp_id',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': int',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.state_serial',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.state_serial',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': int',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.serial_task',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.serial_task',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.status_CM',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.status_CM',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.status_MPP',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.status_MPP',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.client',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.client',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': pymodbus.client.serial.AsyncModbusSerialClient',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.pushButton_connect_Handler',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.pushButton_connect_Handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.serialConnect',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.serialConnect',
			kind: 'function',
			doc: '<p>\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u043a\u043d\u0438\u0435 \u043a \u0414\u0414\u0418\u0418\n\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043f\u0440\u043e\u0438\u0441\u0445\u043e\u0434\u0438\u0442 \u043e\u0434\u043d\u043e\u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u043a \u0426\u041c \u0438 \u041c\u041f\u041f.\n\u0414\u043b\u044f \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043a \u041c\u041f\u041f \u043d\u0443\u0436\u043d\u043e \u0437\u0430\u0434\u0430\u0442\u044c ID.\n\u041f\u0440\u0438 \u0443\u0441\u043f\u0435\u0448\u043d\u043e\u043c \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0438 \u0426\u041c \u0432\u044b\u0434\u0430\u0441\u0442 \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0443 ddii_mpp_data.</p>\n\n<p>Parameters:\nself (\u044d\u043a\u0437\u0435\u043c\u043f\u043b\u044f\u0440 MainUIRenderer): \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u044d\u043a\u0437\u0435\u043c\u043f\u043b\u044f\u0440 \u043a\u043b\u0430\u0441\u0441\u0430 MainUIRenderer.\nid (int): ID MPP.\nbaudrate (int): \u0421\u043a\u043e\u0440\u043e\u0441\u0442\u044c \u043f\u0435\u0440\u0435\u0434\u0430\u0447\u0438 \u0434\u0430\u043d\u043d\u044b\u0445 \u0434\u043b\u044f \u043f\u043e\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u043d\u043e\u0439 \u0441\u0432\u044f\u0437\u0438.\nf_comand (int): \u043a\u043e\u043c\u0430\u043d\u0434\u0430 \u0434\u043b\u044f \u0437\u0430\u043f\u0438\u0441\u0438 \u0432 Modbus.\ndata (int): \u041a\u043e\u043c\u0430\u043d\u0434\u0430 \u0447\u0442\u0435\u043d\u0438\u044f \u0438\u0437 Modbus.</p>\n\n<p>Returns:\nNone</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.check_connect',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.check_connect',
			kind: 'function',
			doc: '<p>\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog.SerialConnect.update_label_connect',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog',
			qualname: 'SerialConnect.update_label_connect',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.src_path',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'src_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: 'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.modules_path',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'modules_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value:
				'PosixPath(&#x27;/Users/vladk/git/ddii/ddii_scopus/modules&#x27;)',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'ModbusRelayServer',
			kind: 'class',
			doc: '<p>\u0421\u0435\u0440\u0432\u0435\u0440 \u0434\u043b\u044f \u0440\u0435\u0442\u0440\u0430\u043d\u0441\u043b\u044f\u0446\u0438\u0438 Modbus \u0434\u0430\u043d\u043d\u044b\u0445</p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer.__init__',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'ModbusRelayServer.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">serial_client</span>, </span><span class="param"><span class="n">host</span><span class="o">=</span><span class="s1">&#39;0.0.0.0&#39;</span>, </span><span class="param"><span class="n">port</span><span class="o">=</span><span class="mi">5012</span></span>)</span>',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer.serial_client',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'ModbusRelayServer.serial_client',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer.host',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'ModbusRelayServer.host',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer.port',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'ModbusRelayServer.port',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer.server',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'ModbusRelayServer.server',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer.context',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'ModbusRelayServer.context',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer.start_server',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'ModbusRelayServer.start_server',
			kind: 'function',
			doc: '<p>\u0417\u0430\u043f\u0443\u0441\u043a TCP \u0441\u0435\u0440\u0432\u0435\u0440\u0430</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer.stop_server',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'ModbusRelayServer.stop_server',
			kind: 'function',
			doc: '<p>\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0430 TCP \u0441\u0435\u0440\u0432\u0435\u0440\u0430</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect',
			kind: 'class',
			doc: '<p>QWidget(parent: Optional[QWidget] = None, flags: Qt.WindowType = Qt.WindowFlags())</p>\n',
			bases: 'PyQt6.QtWidgets.QWidget, src.env_var.EnvironmentVar',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.__init__',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">logger</span>, </span><span class="param"><span class="o">**</span><span class="n">kwargs</span></span>)</span>',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.tabWidget_serial',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.tabWidget_serial',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QTabWidget',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.pushButton_connect_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.pushButton_connect_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.lineEdit_Bauderate_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.lineEdit_Bauderate_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.lineEdit_ID_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.lineEdit_ID_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.widget_led_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.widget_led_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QWidget',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.label_state_w',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.label_state_w',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.horizontalLayout_comport',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.horizontalLayout_comport',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QHBoxLayout',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.lineEdit_ip',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.lineEdit_ip',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.lineEdit_tcp_port',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.lineEdit_tcp_port',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.pushButton_connect_tcp',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.pushButton_connect_tcp',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.widget_led_tcp',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.widget_led_tcp',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QWidget',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.label_tcp',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.label_tcp',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLabel',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.coroutine_finished',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.coroutine_finished',
			kind: 'function',
			doc: "<p>pyqtSignal(*types, name: str = ..., revision: int = ..., arguments: Sequence = ...) -> PYQT_SIGNAL</p>\n\n<p>types is normally a sequence of individual types.  Each type is either a\ntype object or a string that is the name of a C++ type.  Alternatively\neach type could itself be a sequence of types each describing a different\noverloaded signal.\nname is the optional C++ name of the signal.  If it is not specified then\nthe name of the class attribute that is bound to the signal is used.\nrevision is the optional revision of the signal that is exported to QML.\nIf it is not specified then 0 is used.\narguments is the optional sequence of the names of the signal's arguments.</p>\n",
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">unknown</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.tcp_status_changed',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.tcp_status_changed',
			kind: 'function',
			doc: "<p>pyqtSignal(*types, name: str = ..., revision: int = ..., arguments: Sequence = ...) -> PYQT_SIGNAL</p>\n\n<p>types is normally a sequence of individual types.  Each type is either a\ntype object or a string that is the name of a C++ type.  Alternatively\neach type could itself be a sequence of types each describing a different\noverloaded signal.\nname is the optional C++ name of the signal.  If it is not specified then\nthe name of the class attribute that is bound to the signal is used.\nrevision is the optional revision of the signal that is exported to QML.\nIf it is not specified then 0 is used.\narguments is the optional sequence of the names of the signal's arguments.</p>\n",
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">unknown</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.mw',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.mw',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.logger',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.logger',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.comboBox_comm',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.comboBox_comm',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.size_policy',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.size_policy',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QSizePolicy',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.pushButton_connect_flag',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.pushButton_connect_flag',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.mpp_id',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.mpp_id',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': int',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.state_serial',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.state_serial',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': int',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.serial_task',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.serial_task',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.status_CM',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.status_CM',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.status_MPP',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.status_MPP',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.client',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.client',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': pymodbus.client.serial.AsyncModbusSerialClient',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.tcp_client',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.tcp_client',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': pymodbus.client.tcp.AsyncModbusTcpClient',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.relay_server',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.relay_server',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation:
				': ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.ModbusRelayServer',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.server_task',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.server_task',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.tcp_connected',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.tcp_connected',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.server_running',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.server_running',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.update_tcp_interface',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.update_tcp_interface',
			kind: 'function',
			doc: '<p>\u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0430 TCP \u0432 \u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0441\u0442\u0438 \u043e\u0442 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f serial</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">index</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.tcp_button_handler',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.tcp_button_handler',
			kind: 'function',
			doc: '<p>\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u0447\u0438\u043a \u043a\u043d\u043e\u043f\u043a\u0438 TCP</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.tcp_server_handler',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.tcp_server_handler',
			kind: 'function',
			doc: '<p>\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u0447\u0438\u043a \u0434\u043b\u044f \u0440\u0435\u0436\u0438\u043c\u0430 \u0441\u0435\u0440\u0432\u0435\u0440\u0430</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.tcp_client_handler',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.tcp_client_handler',
			kind: 'function',
			doc: '<p>\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u0447\u0438\u043a \u0434\u043b\u044f \u0440\u0435\u0436\u0438\u043c\u0430 \u043a\u043b\u0438\u0435\u043d\u0442\u0430</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.start_tcp_server',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.start_tcp_server',
			kind: 'function',
			doc: '<p>\u0417\u0430\u043f\u0443\u0441\u043a TCP \u0441\u0435\u0440\u0432\u0435\u0440\u0430</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.stop_tcp_server',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.stop_tcp_server',
			kind: 'function',
			doc: '<p>\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0430 TCP \u0441\u0435\u0440\u0432\u0435\u0440\u0430</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.connect_tcp_client',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.connect_tcp_client',
			kind: 'function',
			doc: '<p>\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043a\u0430\u043a TCP \u043a\u043b\u0438\u0435\u043d\u0442</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.disconnect_tcp_client',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.disconnect_tcp_client',
			kind: 'function',
			doc: '<p>\u041e\u0442\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 TCP \u043a\u043b\u0438\u0435\u043d\u0442\u0430</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.update_tcp_status',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.update_tcp_status',
			kind: 'function',
			doc: '<p>\u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0441\u0442\u0430\u0442\u0443\u0441\u0430 TCP</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">message</span>, </span><span class="param"><span class="n">is_connected</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.pushButton_connect_Handler',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.pushButton_connect_Handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.serialConnect',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.serialConnect',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.check_connect',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.check_connect',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp.SerialConnect.update_label_connect',
			modulename: 'ddii_scopus.modules.Main_Serial.main_serial_dialog_tcp',
			qualname: 'SerialConnect.update_label_connect',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Trapezoid',
			modulename: 'ddii_scopus.modules.Main_Trapezoid',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog',
			kind: 'class',
			doc: '<p>QDialog(parent: Optional[QWidget] = None, flags: Qt.WindowType = Qt.WindowFlags())</p>\n',
			bases: 'PyQt6.QtWidgets.QDialog',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.__init__',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">root</span>, </span><span class="param"><span class="o">**</span><span class="n">kwargs</span></span>)</span>',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.pushButton_OK',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.pushButton_OK',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.pushButton_cancel',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.pushButton_cancel',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QPushButton',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.lineEdit_t_decay_pips',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.lineEdit_t_decay_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.lineEdit_t_rise_pips',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.lineEdit_t_rise_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.lineEdit_t_top_pips',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.lineEdit_t_top_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.checkBox_invert_pips',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.checkBox_invert_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QCheckBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.lineEdit_t_decay_sipm',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.lineEdit_t_decay_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.lineEdit_t_rise_sipm',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.lineEdit_t_rise_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.lineEdit_t_top_sipm',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.lineEdit_t_top_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QLineEdit',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.checkBox_invert_sipm',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.checkBox_invert_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QCheckBox',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.horizontalSlider_T_decay_pips',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.horizontalSlider_T_decay_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QSlider',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.horizontalSlider_T_rise_pips',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.horizontalSlider_T_rise_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QSlider',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.horizontalSlider_T_top_pips',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.horizontalSlider_T_top_pips',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QSlider',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.horizontalSlider_T_decay_sipm',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.horizontalSlider_T_decay_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QSlider',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.horizontalSlider_T_rise_sipm',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.horizontalSlider_T_rise_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QSlider',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.horizontalSlider_T_top_sipm',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.horizontalSlider_T_top_sipm',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': PyQt6.QtWidgets.QSlider',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.T_DECAY_PIPS',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.T_DECAY_PIPS',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '0',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.T_RISE_PIPS',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.T_RISE_PIPS',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '1',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.T_TOP_PIPS',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.T_TOP_PIPS',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '2',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.T_DECAY_SIPM',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.T_DECAY_SIPM',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '3',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.T_RISE_SIPM',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.T_RISE_SIPM',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '4',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.T_TOP_SIPM',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.T_TOP_SIPM',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '5',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.root',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.root',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.slider_value_changed',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.slider_value_changed',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">numlineEdit</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.pushButton_OK_handler',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.pushButton_OK_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog.MainTrapezoidDialog.pushButton_pushButton_cancel_handler',
			modulename: 'ddii_scopus.modules.Main_Trapezoid.main_trapezoid_dialog',
			qualname: 'MainTrapezoidDialog.pushButton_pushButton_cancel_handler',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.modules.Main_Waveform_Viewer',
			modulename: 'ddii_scopus.modules.Main_Waveform_Viewer',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.modules.MainUIRenderer',
			modulename: 'ddii_scopus.modules.MainUIRenderer',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src',
			modulename: 'ddii_scopus.src',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.async_task_manager',
			modulename: 'ddii_scopus.src.async_task_manager',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.async_task_manager.PrintLogger',
			modulename: 'ddii_scopus.src.async_task_manager',
			qualname: 'PrintLogger',
			kind: 'class',
			doc: '<p>\u0417\u0430\u043c\u0435\u043d\u044f\u0435\u0442 \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u044b\u0439 \u043b\u043e\u0433\u0433\u0435\u0440, \u0438\u043c\u0438\u0442\u0438\u0440\u0443\u044f \u0435\u0433\u043e \u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441</p>\n',
		},
		{
			fullname: 'ddii_scopus.src.async_task_manager.AsyncTaskManager',
			modulename: 'ddii_scopus.src.async_task_manager',
			qualname: 'AsyncTaskManager',
			kind: 'class',
			doc: '<p>\u041c\u0435\u043d\u0435\u0434\u0436\u0435\u0440 \u0430\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u043d\u044b\u0445 \u0437\u0430\u0434\u0430\u0447: \u0441\u043e\u0437\u0434\u0430\u0451\u0442, \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0435\u0442, \u043e\u0442\u043c\u0435\u043d\u044f\u0435\u0442.</p>\n',
		},
		{
			fullname: 'ddii_scopus.src.async_task_manager.AsyncTaskManager.__init__',
			modulename: 'ddii_scopus.src.async_task_manager',
			qualname: 'AsyncTaskManager.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">logger</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="n">logging</span><span class="o">.</span><span class="n">Logger</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.async_task_manager.AsyncTaskManager.tasks',
			modulename: 'ddii_scopus.src.async_task_manager',
			qualname: 'AsyncTaskManager.tasks',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': Dict[str, _asyncio.Task]',
		},
		{
			fullname: 'ddii_scopus.src.async_task_manager.AsyncTaskManager.logger',
			modulename: 'ddii_scopus.src.async_task_manager',
			qualname: 'AsyncTaskManager.logger',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.src.async_task_manager.AsyncTaskManager.create_task',
			modulename: 'ddii_scopus.src.async_task_manager',
			qualname: 'AsyncTaskManager.create_task',
			kind: 'function',
			doc: '<p>\u0421\u043e\u0437\u0434\u0430\u0451\u0442 \u0437\u0430\u0434\u0430\u0447\u0443, \u0435\u0441\u043b\u0438 \u043e\u043d\u0430 \u0435\u0449\u0451 \u043d\u0435 \u0430\u043a\u0442\u0438\u0432\u043d\u0430.</p>\n\n<h6 id="parameters">Parameters</h6>\n\n<ul>\n<li><strong>coroutine</strong>:  \u0432\u044b\u0437\u0432\u0430\u043d\u043d\u0430\u044f \u043a\u043e\u0440\u0443\u0442\u0438\u043d\u0430</li>\n<li><strong>task_name</strong>:  \u0443\u043d\u0438\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0438\u043c\u044f \u0437\u0430\u0434\u0430\u0447\u0438</li>\n</ul>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="bp">self</span>,</span><span class="param">\t<span class="n">coroutine</span><span class="p">:</span> <span class="n">Coroutine</span><span class="p">[</span><span class="n">typing</span><span class="o">.</span><span class="n">Any</span><span class="p">,</span> <span class="n">typing</span><span class="o">.</span><span class="n">Any</span><span class="p">,</span> <span class="n">typing</span><span class="o">.</span><span class="n">Any</span><span class="p">]</span>,</span><span class="param">\t<span class="n">task_name</span><span class="p">:</span> <span class="nb">str</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.src.async_task_manager.AsyncTaskManager.cancel_task',
			modulename: 'ddii_scopus.src.async_task_manager',
			qualname: 'AsyncTaskManager.cancel_task',
			kind: 'function',
			doc: '<p>\u041e\u0442\u043c\u0435\u043d\u044f\u0435\u0442 \u0437\u0430\u0434\u0430\u0447\u0443 \u043f\u043e \u0438\u043c\u0435\u043d\u0438.</p>\n\n<h6 id="parameters">Parameters</h6>\n\n<ul>\n<li><strong>task_name</strong>:  \u0438\u043c\u044f \u0437\u0430\u0434\u0430\u0447\u0438</li>\n</ul>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">task_name</span><span class="p">:</span> <span class="nb">str</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.src.async_task_manager.AsyncTaskManager.cancel_all_tasks',
			modulename: 'ddii_scopus.src.async_task_manager',
			qualname: 'AsyncTaskManager.cancel_all_tasks',
			kind: 'function',
			doc: '<p>\u041e\u0442\u043c\u0435\u043d\u044f\u0435\u0442 \u0432\u0441\u0435 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0435 \u0437\u0430\u0434\u0430\u0447\u0438.</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname:
				'ddii_scopus.src.async_task_manager.AsyncTaskManager.get_active_tasks',
			modulename: 'ddii_scopus.src.async_task_manager',
			qualname: 'AsyncTaskManager.get_active_tasks',
			kind: 'function',
			doc: '<p>\u0412\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u0442 \u0441\u043f\u0438\u0441\u043e\u043a \u0438\u043c\u0451\u043d \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 (\u043d\u0435 \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d\u043d\u044b\u0445) \u0437\u0430\u0434\u0430\u0447.</p>\n\n<h6 id="returns">Returns</h6>\n\n<blockquote>\n  <p>\u0441\u043f\u0438\u0441\u043e\u043a \u0441\u0442\u0440\u043e\u043a \u0441 \u0438\u043c\u0435\u043d\u0430\u043c\u0438 \u0437\u0430\u0434\u0430\u0447</p>\n</blockquote>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="n">List</span><span class="p">[</span><span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.craft_custom_widget',
			modulename: 'ddii_scopus.src.craft_custom_widget',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.craft_custom_widget.add_serial_widget',
			modulename: 'ddii_scopus.src.craft_custom_widget',
			qualname: 'add_serial_widget',
			kind: 'function',
			doc: '<p>\u0414\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u0432\u0438\u0434\u0436\u0435\u0442 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f \u0441\u0435\u0440\u0438\u0430\u043b \u0432 layout \u0433\u043b\u0430\u0432\u043d\u043e\u0433\u043e \u043e\u043a\u043d\u0430\nArgs:\n    vlayout_ser_connect ([QtWidgets.QVBoxLayout]): layout \u0433\u043b\u0430\u0432\u043d\u043e\u0433\u043e \u043e\u043a\u043d\u0430\n    w_ser_dialog ([QtWidgets.QDialog]): \u0432\u0438\u0434\u0436\u0435\u0442 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f \u0441\u0435\u0440\u0438\u0430\u043b</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">vlayout_ser_connect</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QVBoxLayout</span>, </span><span class="param"><span class="n">w_ser_dialog</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.customComboBox_COMport',
			modulename: 'ddii_scopus.src.customComboBox_COMport',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.customComboBox_COMport.CustomComboBox_COMport',
			modulename: 'ddii_scopus.src.customComboBox_COMport',
			qualname: 'CustomComboBox_COMport',
			kind: 'class',
			doc: '<p>QComboBox(parent: Optional[QWidget] = None)</p>\n',
			bases: 'PyQt6.QtWidgets.QComboBox',
		},
		{
			fullname:
				'ddii_scopus.src.customComboBox_COMport.CustomComboBox_COMport.__init__',
			modulename: 'ddii_scopus.src.customComboBox_COMport',
			qualname: 'CustomComboBox_COMport.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">parent</span><span class="o">=</span><span class="kc">None</span></span>)</span>',
		},
		{
			fullname:
				'ddii_scopus.src.customComboBox_COMport.CustomComboBox_COMport.clickEvent',
			modulename: 'ddii_scopus.src.customComboBox_COMport',
			qualname: 'CustomComboBox_COMport.clickEvent',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname:
				'ddii_scopus.src.customComboBox_COMport.CustomComboBox_COMport.mousePressEvent',
			modulename: 'ddii_scopus.src.customComboBox_COMport',
			qualname: 'CustomComboBox_COMport.mousePressEvent',
			kind: 'function',
			doc: '<p>mousePressEvent(self, e: Optional[QMouseEvent])</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">event</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command',
			modulename: 'ddii_scopus.src.ddii_command',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand',
			kind: 'class',
			doc: '<p></p>\n',
			bases: 'src.env_var.EnvironmentVar',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.__init__',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">client</span>, </span><span class="param"><span class="n">logger</span>, </span><span class="param"><span class="o">**</span><span class="n">kwargs</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.mw',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.mw',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.client',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.client',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': pymodbus.client.serial.AsyncModbusSerialClient',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.logger',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.logger',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.get_cfg_voltage',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.get_cfg_voltage',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.src.ddii_command.ModbusCMCommand.set_csa_test_enable',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.set_csa_test_enable',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">state</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.set_mode',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.set_mode',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">mode</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.src.ddii_command.ModbusCMCommand.get_desired_voltage',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.get_desired_voltage',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.get_cfg_pwm',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.get_cfg_pwm',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.get_term',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.get_term',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.get_cfg_a_b',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.get_cfg_a_b',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.get_telemetry',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.get_telemetry',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.get_cfg_ddii',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.get_cfg_ddii',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.set_cfg_ddii',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.set_cfg_ddii',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span> <span class="o">|</span> <span class="nb">int</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.get_voltage',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.get_voltage',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.switch_power',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.switch_power',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.set_voltage_pwm',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.set_voltage_pwm',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusCMCommand.set_cfg_a_b',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusCMCommand.set_cfg_a_b',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand',
			kind: 'class',
			doc: '<p>\u0420\u0435\u0433\u0438\u0441\u0442\u0440 0x00 ..... 0x00 0x01\n                        |    |\u2014\u043a\u043e\u043c\u0430\u043d\u0434\u0430 \u041c\u041f\u041f\n                        |\u2014\u043a\u0430\u043d\u0430\u043b \u041c\u041f\u041f (0, 1) </p>\n\n<p>Args:\n    EnvironmentVar (_type_): \u0432\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u0438\u0435 \u043f\u043e\u0441\u0442\u043e\u044f\u043d\u043d\u044b\u0435 \u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\u044f</p>\n',
			bases: 'src.env_var.EnvironmentVar',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.__init__',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">client</span>, </span><span class="param"><span class="n">logger</span>, </span><span class="param"><span class="o">*</span><span class="n">args</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.mw',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.mw',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.client',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.client',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': pymodbus.client.serial.AsyncModbusSerialClient',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.logger',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.logger',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.MPP_ID',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.MPP_ID',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.read_oscill',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.read_oscill',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">ch</span><span class="p">:</span> <span class="nb">int</span> <span class="o">=</span> <span class="mi">0</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.get_hist_32',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.get_hist_32',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.get_hist_16',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.get_hist_16',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.get_mpp_struct',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.get_mpp_struct',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.calibrate_ACQ',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.calibrate_ACQ',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.issue_waveform',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.issue_waveform',
			kind: 'function',
			doc: '<p>\u0412\u044b\u0434\u0430\u0442\u044c waveform\nReturns:\n    bytes</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.start_measure',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.start_measure',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">ch</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span>, </span><span class="param"><span class="n">on</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span> <span class="o">=</span> <span class="mi">1</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.get_hist32',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.get_hist32',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.get_hist16',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.get_hist16',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.get_hcp_hist',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.get_hcp_hist',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.clear_hcp_hist',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.clear_hcp_hist',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.clear_hist',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.clear_hist',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname:
				'ddii_scopus.src.ddii_command.ModbusMPPCommand.start_measure_forced',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.start_measure_forced',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">ch</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.stop_measure',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.stop_measure',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">ch</span><span class="p">:</span> <span class="nb">int</span> <span class="o">|</span> <span class="kc">None</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.set_hh',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.set_hh',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">hh</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.set_level',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.set_level',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">lvl</span><span class="p">:</span> <span class="nb">int</span>, </span><span class="param"><span class="n">ch</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.get_hh',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.get_hh',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.ddii_command.ModbusMPPCommand.get_level',
			modulename: 'ddii_scopus.src.ddii_command',
			qualname: 'ModbusMPPCommand.get_level',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.env_var',
			modulename: 'ddii_scopus.src.env_var',
			kind: 'module',
			doc: '<p>\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u044f \u0432\u0441\u0435\u0445 \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445 \u043f\u0440\u043e\u0435\u043a\u0442\u0430</p>\n',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar',
			kind: 'class',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.HEAD',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.HEAD',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '4081',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.DDII_SWITCH_MODE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.DDII_SWITCH_MODE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '1',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.DDII_UPDATE_DATA',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.DDII_UPDATE_DATA',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '2',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CM_ID',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CM_ID',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '1',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.MPP_ID_DEFAULT',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.MPP_ID_DEFAULT',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '14',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_GET_TELEMETRY',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_GET_TELEMETRY',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '0',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_SWITCH_MODE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_SWITCH_MODE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '1',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_UPDATE_DATA',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_UPDATE_DATA',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '2',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_DBG_RESET',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_DBG_RESET',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '3',
		},
		{
			fullname:
				'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_CSA_TEST_ENABLE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_CSA_TEST_ENABLE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '4',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_SET_CFG',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_SET_CFG',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '5',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_SET_VOLTAGE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_SET_VOLTAGE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '6',
		},
		{
			fullname:
				'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_GET_CFG_VOLTAGE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_GET_CFG_VOLTAGE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '7',
		},
		{
			fullname:
				'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_SET_DEFAULT_CFG',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_SET_DEFAULT_CFG',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '8',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_GET_VOLTAGE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_GET_VOLTAGE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '9',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_GET_CFG_PWM',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_GET_CFG_PWM',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '10',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_HVIP_ON_OFF',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_HVIP_ON_OFF',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '11',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CMD_DBG_GET_CFG',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CMD_DBG_GET_CFG',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '12',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CM_DBG_SET_HVIP_AB',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CM_DBG_SET_HVIP_AB',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '13',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CM_DBG_GET_HVIP_AB',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CM_DBG_GET_HVIP_AB',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '14',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CM_GET_TERM',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CM_GET_TERM',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '15',
		},
		{
			fullname:
				'ddii_scopus.src.env_var.EnvironmentVar.CM_DBG_GET_DESIRED_HVIP',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CM_DBG_GET_DESIRED_HVIP',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '17',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_MPP_COMMAND',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_MPP_COMMAND',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '0',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_MPP_ISSUE_WAVEFORM',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_MPP_ISSUE_WAVEFORM',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '9',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_MPP_HH',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_MPP_HH',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '10',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_GET_MPP_STRUCT',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_GET_MPP_STRUCT',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '6',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_MPP_HIST_32',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_MPP_HIST_32',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '20',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_MPP_HIST_16',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_MPP_HIST_16',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '32',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_MPP_HIST_HCP',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_MPP_HIST_HCP',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '38',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_MPP_LEVEL',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_MPP_LEVEL',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '121',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_CALIBR_ALL_CH',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_CALIBR_ALL_CH',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '80',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_OSCILL_CH0',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_OSCILL_CH0',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '40960',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_OSCILL_CH1',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_OSCILL_CH1',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '41472',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.MPP_LEVEL_TRIG',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.MPP_LEVEL_TRIG',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '1',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.MPP_TRIG_CNT_CLEAR',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.MPP_TRIG_CNT_CLEAR',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '11',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.MPP_START_MEASURE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.MPP_START_MEASURE',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': list[int]',
			default_value: '[2, 1]',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.MPP_STOP_MEASURE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.MPP_STOP_MEASURE',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': list[int]',
			default_value: '[2, 0]',
		},
		{
			fullname:
				'ddii_scopus.src.env_var.EnvironmentVar.MPP_START_MEASURE_FORCED',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.MPP_START_MEASURE_FORCED',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '81',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.MB_F_CODE_16',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.MB_F_CODE_16',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '16',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.MB_F_CODE_3',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.MB_F_CODE_3',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '3',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.MB_F_CODE_6',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.MB_F_CODE_6',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '6',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.REG_COMMAND',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.REG_COMMAND',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '0',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.DEBUG_MODE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.DEBUG_MODE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '12',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.COMBAT_MODE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.COMBAT_MODE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '14',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CONSTANT_MODE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CONSTANT_MODE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '15',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.SILENT_MODE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.SILENT_MODE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '13',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.PIPS_CH_VOLTAGE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.PIPS_CH_VOLTAGE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '1',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.SIPM_CH_VOLTAGE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.SIPM_CH_VOLTAGE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '2',
		},
		{
			fullname: 'ddii_scopus.src.env_var.EnvironmentVar.CHERENKOV_CH_VOLTAGE',
			modulename: 'ddii_scopus.src.env_var',
			qualname: 'EnvironmentVar.CHERENKOV_CH_VOLTAGE',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: '3',
		},
		{
			fullname: 'ddii_scopus.src.event',
			modulename: 'ddii_scopus.src.event',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.event.event',
			modulename: 'ddii_scopus.src.event.event',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.event.event.Event',
			modulename: 'ddii_scopus.src.event.event',
			qualname: 'Event',
			kind: 'class',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.event.event.Event.__init__',
			modulename: 'ddii_scopus.src.event.event',
			qualname: 'Event.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="o">*</span><span class="n">args</span><span class="p">:</span> <span class="n">Type</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.event.event.Event.lock',
			modulename: 'ddii_scopus.src.event.event',
			qualname: 'Event.lock',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': &lt;function RLock at 0x10d6e3e20&gt;',
			default_value: '&lt;unlocked _thread.RLock object owner=0 count=0&gt;',
		},
		{
			fullname: 'ddii_scopus.src.event.event.Event.subscribers',
			modulename: 'ddii_scopus.src.event.event',
			qualname: 'Event.subscribers',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': list[typing.Callable]',
		},
		{
			fullname: 'ddii_scopus.src.event.event.Event.args',
			modulename: 'ddii_scopus.src.event.event',
			qualname: 'Event.args',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': tuple[typing.Type, ...]',
		},
		{
			fullname: 'ddii_scopus.src.event.event.Event.subscribe',
			modulename: 'ddii_scopus.src.event.event',
			qualname: 'Event.subscribe',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">func</span><span class="p">:</span> <span class="n">Callable</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.event.event.Event.unsubscribe',
			modulename: 'ddii_scopus.src.event.event',
			qualname: 'Event.unsubscribe',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">func</span><span class="p">:</span> <span class="n">Callable</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.event.event.Event.emit',
			modulename: 'ddii_scopus.src.event.event',
			qualname: 'Event.emit',
			kind: 'function',
			doc: '<p>\u041f\u043e\u0442\u043e\u043a\u043e\u0432\u044b\u0439 \u0438\u0437\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u044c</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="o">*</span><span class="n">args</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.filtrs_data',
			modulename: 'ddii_scopus.src.filtrs_data',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.filtrs_data.FiltrsData',
			modulename: 'ddii_scopus.src.filtrs_data',
			qualname: 'FiltrsData',
			kind: 'class',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.filtrs_data.FiltrsData.filters',
			modulename: 'ddii_scopus.src.filtrs_data',
			qualname: 'FiltrsData.filters',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.filtrs_data.FiltrsData.threshold_filter',
			modulename: 'ddii_scopus.src.filtrs_data',
			qualname: 'FiltrsData.threshold_filter',
			kind: 'function',
			doc: '<p>\u0424\u0438\u043b\u044c\u0442\u0440 \u043f\u043e \u043f\u043e\u0440\u043e\u0433\u0443, \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u0442 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435, \u0435\u0441\u043b\u0438 \u043e\u043d\u043e \u0431\u043e\u043b\u044c\u0448\u0435 \u043f\u043e\u0440\u043e\u0433\u0430</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span>, </span><span class="param"><span class="n">threshold</span><span class="p">:</span> <span class="nb">float</span> <span class="o">=</span> <span class="mi">10</span></span><span class="return-annotation">) -> <span class="nb">int</span> <span class="o">|</span> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.filtrs_data.FiltrsData.median_filter',
			modulename: 'ddii_scopus.src.filtrs_data',
			qualname: 'FiltrsData.median_filter',
			kind: 'function',
			doc: '<p>\u041c\u0435\u0434\u0438\u0430\u043d\u043d\u044b\u0439 \u0444\u0438\u043b\u044c\u0442\u0440 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0445 N \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0439</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span> <span class="o">|</span> <span class="nb">float</span><span class="p">]</span>, </span><span class="param"><span class="n">window_size</span><span class="p">:</span> <span class="nb">int</span> <span class="o">=</span> <span class="mi">5</span></span><span class="return-annotation">) -> <span class="nb">float</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.filtrs_data.FiltrsData.moving_average_filter',
			modulename: 'ddii_scopus.src.filtrs_data',
			qualname: 'FiltrsData.moving_average_filter',
			kind: 'function',
			doc: '<p>\u0421\u043a\u043e\u043b\u044c\u0437\u044f\u0449\u0435\u0435 \u0441\u0440\u0435\u0434\u043d\u0435\u0435 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0445 N \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0439</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span> <span class="o">|</span> <span class="nb">float</span><span class="p">]</span>, </span><span class="param"><span class="n">window_size</span><span class="p">:</span> <span class="nb">int</span> <span class="o">=</span> <span class="mi">5</span></span><span class="return-annotation">) -> <span class="nb">float</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.filtrs_data.FiltrsData.exp_smoothing_filter',
			modulename: 'ddii_scopus.src.filtrs_data',
			qualname: 'FiltrsData.exp_smoothing_filter',
			kind: 'function',
			doc: '<p>\u042d\u043a\u0441\u043f\u043e\u043d\u0435\u043d\u0446\u0438\u0430\u043b\u044c\u043d\u043e\u0435 \u0441\u0433\u043b\u0430\u0436\u0438\u0432\u0430\u043d\u0438\u0435</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span> <span class="o">|</span> <span class="nb">float</span><span class="p">]</span>, </span><span class="param"><span class="n">alpha</span><span class="p">:</span> <span class="nb">float</span> <span class="o">=</span> <span class="mf">0.3</span></span><span class="return-annotation">) -> <span class="nb">float</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.log_config',
			modulename: 'ddii_scopus.src.log_config',
			kind: 'module',
			doc: '<p>\u041b\u043e\u0433 \u043a\u043e\u043d\u0444\u0438\u0433\u0438.\n"DEBUG" - \u0434\u043b\u044f \u0437\u0430\u043f\u0438\u0441\u0438 \u043e\u0442\u043b\u0430\u0434\u043e\u0447\u043d\u043e\u0439 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438\n"ERROR" - \u0434\u043b\u044f \u0437\u0430\u043f\u0438\u0441\u0438 \u043e\u0448\u0438\u0431\u043e\u043a \u0432 \u0436\u0443\u0440\u043d\u0430\u043b \u043e\u0448\u0438\u0431\u043e\u043a\n"INFO" - \u0434\u043b\u044f \u0437\u0430\u043f\u0438\u0441\u0438 \u043a\u043e\u043c\u0430\u043d\u0434 serial port \u043a\u0430\u043a \u0432 DockLight</p>\n',
		},
		{
			fullname: 'ddii_scopus.src.log_config.log_init',
			modulename: 'ddii_scopus.src.log_config',
			qualname: 'log_init',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.log_config.emulator_filter',
			modulename: 'ddii_scopus.src.log_config',
			qualname: 'emulator_filter',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">record</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.log_config.tx_filter',
			modulename: 'ddii_scopus.src.log_config',
			qualname: 'tx_filter',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">record</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.log_config.rx_filter',
			modulename: 'ddii_scopus.src.log_config',
			qualname: 'rx_filter',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">record</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.log_config.debug_filter',
			modulename: 'ddii_scopus.src.log_config',
			qualname: 'debug_filter',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">record</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.log_config.error_filter',
			modulename: 'ddii_scopus.src.log_config',
			qualname: 'error_filter',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">record</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.log_config.warning_filter',
			modulename: 'ddii_scopus.src.log_config',
			qualname: 'warning_filter',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">record</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.log_config.log_s',
			modulename: 'ddii_scopus.src.log_config',
			qualname: 'log_s',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">message</span><span class="p">:</span> <span class="nb">list</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.main_window_maker',
			modulename: 'ddii_scopus.src.main_window_maker',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.main_window_maker.create_split_widget',
			modulename: 'ddii_scopus.src.main_window_maker',
			qualname: 'create_split_widget',
			kind: 'function',
			doc: '<p>\u0421\u043e\u0437\u0434\u0430\u0435\u0442 \u0438 \u0434\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u0432 layout \u0440\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u0435\u043b\u044c (QSplitter) \u0441 \u0434\u0432\u0443\u043c\u044f \u0432\u0438\u0434\u0436\u0435\u0442\u0430\u043c\u0438.</p>\n\n<p>\u0424\u0443\u043d\u043a\u0446\u0438\u044f \u043f\u0440\u0438\u043d\u0438\u043c\u0430\u0435\u0442 \u043e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 QGridLayout \u0438 \u0434\u0432\u0430 \u0432\u0438\u0434\u0436\u0435\u0442\u0430 (\u043e\u0431\u044b\u0447\u043d\u043e QTabWidget), \n\u0441\u043e\u0437\u0434\u0430\u0435\u0442 \u0433\u043e\u0440\u0438\u0437\u043e\u043d\u0442\u0430\u043b\u044c\u043d\u044b\u0439 QSplitter, \u0440\u0430\u0437\u043c\u0435\u0449\u0430\u0435\u0442 \u0432 \u043d\u0435\u043c \u043e\u0431\u0430 \u0432\u0438\u0434\u0436\u0435\u0442\u0430 \n\u0438 \u0434\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u0440\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u0435\u043b\u044c \u0432 \u0443\u043a\u0430\u0437\u0430\u043d\u043d\u044b\u0439 layout.</p>\n\n<p>Args:\n    gridLayout_main_split (QGridLayout): \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 layout, \u0432 \u043a\u043e\u0442\u043e\u0440\u044b\u0439 \u0431\u0443\u0434\u0435\u0442 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d QSplitter.\n    left_widget (QTabWidget): \u0412\u0438\u0434\u0436\u0435\u0442, \u043a\u043e\u0442\u043e\u0440\u044b\u0439 \u0431\u0443\u0434\u0435\u0442 \u0440\u0430\u0437\u043c\u0435\u0449\u0435\u043d \u0441\u043b\u0435\u0432\u0430 \u0432 QSplitter.\n    right_widget (QTabWidget): \u0412\u0438\u0434\u0436\u0435\u0442, \u043a\u043e\u0442\u043e\u0440\u044b\u0439 \u0431\u0443\u0434\u0435\u0442 \u0440\u0430\u0437\u043c\u0435\u0449\u0435\u043d \u0441\u043f\u0440\u0430\u0432\u0430 \u0432 QSplitter.</p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">gridLayout_main_split</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QGridLayout</span>,</span><span class="param">\t<span class="n">left_widget</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QWidget</span>,</span><span class="param">\t<span class="n">right_widget</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QTabWidget</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.main_window_maker.replace_left_widget',
			modulename: 'ddii_scopus.src.main_window_maker',
			qualname: 'replace_left_widget',
			kind: 'function',
			doc: '<p>\u0417\u0430\u043c\u0435\u043d\u044f\u0435\u0442 \u043b\u0435\u0432\u044b\u0439 \u0432\u0438\u0434\u0436\u0435\u0442 \u0432 \u0441\u043f\u043b\u0438\u0442\u0442\u0435\u0440\u0435</p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">old_left_widget</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QWidget</span>,</span><span class="param">\t<span class="n">new_left_widget</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QWidget</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.main_window_maker.create_tab_widget_items',
			modulename: 'ddii_scopus.src.main_window_maker',
			qualname: 'create_tab_widget_items',
			kind: 'function',
			doc: '<p>\u0421\u043e\u0437\u0434\u0430\u0435\u0442 \u0438 \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u0442 QTabWidget \u0441 \u043e\u0440\u0433\u0430\u043d\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u043c\u0438 \u0432\u043a\u043b\u0430\u0434\u043a\u0430\u043c\u0438 \u0432\u0438\u0434\u0436\u0435\u0442\u043e\u0432.\n\u0424\u0443\u043d\u043a\u0446\u0438\u044f \u0441\u043e\u0437\u0434\u0430\u0435\u0442 \u043c\u043d\u043e\u0433\u043e\u0443\u0440\u043e\u0432\u043d\u0435\u0432\u044b\u0439 \u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441 \u0441:</p>\n\n<ul>\n<li>\u0412\u043a\u043b\u0430\u0434\u043a\u0430\u043c\u0438 (QTabWidget)</li>\n<li>\u041f\u0440\u043e\u043a\u0440\u0443\u0447\u0438\u0432\u0430\u0435\u043c\u044b\u043c\u0438 \u043e\u0431\u043b\u0430\u0441\u0442\u044f\u043c\u0438 (QScrollArea) </li>\n<li>\u0413\u0440\u0443\u043f\u043f\u043e\u0432\u044b\u043c\u0438 \u0431\u043b\u043e\u043a\u0430\u043c\u0438 (QGroupBox) \u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0432\u0438\u0434\u0436\u0435\u0442\u0430</li>\n</ul>\n\n<p>:Args:\n    widget_model (Dict[str, Dict[str, QWidget]]): \n        \u0418\u0435\u0440\u0430\u0440\u0445\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0430 \u0432\u0438\u0434\u0436\u0435\u0442\u043e\u0432:\n            - \u041a\u043b\u044e\u0447 1 \u0443\u0440\u043e\u0432\u043d\u044f: \u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0432\u043a\u043b\u0430\u0434\u043a\u0438 (str)\n            - \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435: \u0421\u043b\u043e\u0432\u0430\u0440\u044c {\n                "\u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0432\u0438\u0434\u0436\u0435\u0442\u0430": QWidget-\u043e\u0431\u044a\u0435\u043a\u0442\n            }\n    tab_widget_handler (Optional[Callable] = None): \n    \u041e\u0431\u0440\u0430\u0431\u043e\u0442\u0447\u0438\u043a \u0441\u043e\u0431\u044b\u0442\u0438\u0439 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0432\u043a\u043b\u0430\u0434\u043e\u043a tabwidget.</p>\n\n<p>:Return:</p>\n\n<pre><code>QTabWidget: \u0413\u043e\u0442\u043e\u0432\u044b\u0439 \u0432\u0438\u0434\u0436\u0435\u0442 \u0441 \u0432\u043a\u043b\u0430\u0434\u043a\u0430\u043c\u0438, \u0441\u043e\u0434\u0435\u0440\u0436\u0430\u0449\u0438\u0439:\n    - \u041a\u0430\u0436\u0434\u0430\u044f \u0432\u043a\u043b\u0430\u0434\u043a\u0430 \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442 ScrollArea\n    - \u041a\u0430\u0436\u0434\u044b\u0439 \u0432\u0438\u0434\u0436\u0435\u0442 \u043e\u0444\u043e\u0440\u043c\u043b\u0435\u043d \u0432 GroupBox\n    - \u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u043e\u0442\u0441\u0442\u0443\u043f\u044b \u0438 \u0440\u0430\u0437\u043c\u0435\u0440\u044b\n    - \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u043e\u0435 \u0444\u043e\u0440\u043c\u0430\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0448\u0440\u0438\u0444\u0442\u043e\u0432\n</code></pre>\n\n<p>:Example:\n    widget_structure = {</p>\n\n<pre><code>    "\u0413\u0440\u0430\u0444\u0438\u043a\u0438": {\n        "\u0413\u0440\u0430\u0444\u0438\u043a 1": GraphWidget(),\n        "\u0413\u0440\u0430\u0444\u0438\u043a 2": GraphWidget()},\n\n    "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438": {\n        "\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b": SettingsWidget()}\n}\ntab_widget = create_tab_widget_items(widget_structure)\n</code></pre>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">widget_model</span><span class="p">:</span> <span class="n">Dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="n">Dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QWidget</span><span class="p">]]</span>,</span><span class="param">\t<span class="n">tab_widget_handler</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="n">Callable</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span></span><span class="return-annotation">) -> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QTabWidget</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker',
			modulename: 'ddii_scopus.src.modbus_worker',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.SendFilter',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'SendFilter',
			kind: 'class',
			doc: '<p>Filter instances are used to perform arbitrary filtering of LogRecords.</p>\n\n<p>Loggers and Handlers can optionally use Filter instances to filter\nrecords as desired. The base filter class only allows events which are\nbelow a certain point in the logger hierarchy. For example, a filter\ninitialized with "A.B" will allow events logged by loggers "A.B",\n"A.B.C", "A.B.C.D", "A.B.D" etc. but not "A.BB", "B.A.B" etc. If\ninitialized with the empty string, all events are passed.</p>\n',
			bases: 'logging.Filter',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.SendFilter.filter',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'SendFilter.filter',
			kind: 'function',
			doc: '<p>Determine if the specified record is to be logged.</p>\n\n<p>Returns True if the record should be logged, or False otherwise.\nIf deemed appropriate, the record may be modified in-place.</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">record</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.SendHandler',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'SendHandler',
			kind: 'class',
			doc: "<p>Handler instances dispatch logging events to specific destinations.</p>\n\n<p>The base handler class. Acts as a placeholder which defines the Handler\ninterface. Handlers can optionally use Formatter instances to format\nrecords as desired. By default, no formatter is specified; in this case,\nthe 'raw' message as determined by record.message is logged.</p>\n",
			bases: 'logging.Handler',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.SendHandler.__init__',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'SendHandler.__init__',
			kind: 'function',
			doc: '<p>Initializes the instance - basically setting the formatter to None\nand the filter list to empty.</p>\n',
			signature: '<span class="signature pdoc-code condensed">()</span>',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.SendHandler.mess',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'SendHandler.mess',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.SendHandler.emit',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'SendHandler.emit',
			kind: 'function',
			doc: '<p>Do whatever it takes to actually log the specified logging record.</p>\n\n<p>This version is intended to be implemented by subclasses and so\nraises a NotImplementedError.</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">record</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.ModbusWorkerLog',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'ModbusWorkerLog',
			kind: 'class',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.ModbusWorkerLog.__init__',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'ModbusWorkerLog.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="o">**</span><span class="n">kwargs</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.ModbusWorkerLog.send_handler',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'ModbusWorkerLog.send_handler',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.ModbusWorker',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'ModbusWorker',
			kind: 'class',
			doc: '<p></p>\n',
			bases: 'ModbusWorkerLog',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.ModbusWorker.__init__',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'ModbusWorker.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="o">**</span><span class="n">kwargs</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.ModbusWorker.byte_to_float',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'ModbusWorker.byte_to_float',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">byte_str</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">float</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.modbus_worker.ModbusWorker.float_to_byte',
			modulename: 'ddii_scopus.src.modbus_worker',
			qualname: 'ModbusWorker.float_to_byte',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">val</span><span class="p">:</span> <span class="nb">float</span></span><span class="return-annotation">) -> <span class="nb">bytes</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.parsers',
			modulename: 'ddii_scopus.src.parsers',
			kind: 'module',
			doc: '<p>\u0420\u0430\u0437\u043b\u0438\u0447\u043d\u044b\u0435 \u043f\u0430\u0440\u0441\u0435\u0440\u044b\n\u041f\u0430\u0440\u0441\u0435\u0440 \u0434\u0430\u043d\u043d\u044b\u0445 \u043c\u043f\u043f\n\u041f\u0430\u0440\u0441\u0435\u0440 log</p>\n',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers',
			kind: 'class',
			doc: '<p></p>\n',
			bases: 'src.modbus_worker.ModbusWorker',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.__init__',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="o">**</span><span class="n">kwargs</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.pars_telemetria',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.pars_telemetria',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">tel</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.pars_cfg_ddii',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.pars_cfg_ddii',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">b</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.pars_mpp_hh',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.pars_mpp_hh',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">b</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.pars_mpp_lvl',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.pars_mpp_lvl',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">b</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.pars_voltage',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.pars_voltage',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data_v</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.pars_cfg_volt',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.pars_cfg_volt',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data_v</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.pars_cfg_pwm',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.pars_cfg_pwm',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data_v</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.pars_cfg_a_b',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.pars_cfg_a_b',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data_v</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.pars_everything',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.pars_everything',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="bp">self</span>,</span><span class="param">\t<span class="n">dataObj</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="n">src</span><span class="o">.</span><span class="n">parsers_pack</span><span class="o">.</span><span class="n">LineEObj</span><span class="p">]</span>,</span><span class="param">\t<span class="n">bytes_data</span><span class="p">:</span> <span class="nb">bytes</span>,</span><span class="param">\t<span class="n">endian</span><span class="p">:</span> <span class="nb">str</span></span><span class="return-annotation">) -> <span class="nb">dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="nb">str</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.mpp_pars_16b',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.mpp_pars_16b',
			kind: 'function',
			doc: '<p>\u041f\u0440\u0435\u043e\u0431\u0440\u0430\u0437\u0443\u0435\u0442 \u043a\u0432\u0430\u043d\u0442\u044b \u0410\u0426\u041f \u0432 int</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers.Parsers.mpp_pars_32b',
			modulename: 'ddii_scopus.src.parsers',
			qualname: 'Parsers.mpp_pars_32b',
			kind: 'function',
			doc: '<p>\u041f\u0440\u0435\u043e\u0431\u0440\u0430\u0437\u0443\u0435\u0442 \u043a\u0432\u0430\u043d\u0442\u044b \u0410\u0426\u041f \u0432 int</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">data</span><span class="p">:</span> <span class="nb">bytes</span></span><span class="return-annotation">) -> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span><span class="p">]</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.parsers_pack',
			modulename: 'ddii_scopus.src.parsers_pack',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.parsers_pack.LineEObj',
			modulename: 'ddii_scopus.src.parsers_pack',
			qualname: 'LineEObj',
			kind: 'class',
			doc: '<p>key: str - \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u043e\u0439</p>\n\n<p>lineobj: QLineEdit - \u043e\u0431\u044a\u0435\u043a\u0442 QLineEdit</p>\n\n<p>tp: str - \u0442\u0438\u043f \u0434\u0430\u043d\u043d\u044b\u0445 \u0437\u0430\u043f\u0438\u0441\u0430\u043d\u043d\u044b\u0439 \u0432 QLineEdit,\n\u043d\u0443\u0436\u043d\u043e \u0447\u0442\u043e\u0431\u044b \u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e \u0438\u0437\u0432\u043b\u0435\u0447\u044c \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 QLineEdit</p>\n',
		},
		{
			fullname: 'ddii_scopus.src.parsers_pack.LineEObj.__init__',
			modulename: 'ddii_scopus.src.parsers_pack',
			qualname: 'LineEObj.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">key</span><span class="p">:</span> <span class="nb">str</span>, </span><span class="param"><span class="n">lineobj_txt</span><span class="p">:</span> <span class="nb">str</span>, </span><span class="param"><span class="n">tp</span><span class="p">:</span> <span class="nb">str</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.parsers_pack.LineEObj.key',
			modulename: 'ddii_scopus.src.parsers_pack',
			qualname: 'LineEObj.key',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': str',
		},
		{
			fullname: 'ddii_scopus.src.parsers_pack.LineEObj.lineobj_txt',
			modulename: 'ddii_scopus.src.parsers_pack',
			qualname: 'LineEObj.lineobj_txt',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': str',
		},
		{
			fullname: 'ddii_scopus.src.parsers_pack.LineEObj.tp',
			modulename: 'ddii_scopus.src.parsers_pack',
			qualname: 'LineEObj.tp',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': str',
		},
		{
			fullname: 'ddii_scopus.src.parsers_pack.LineEditPack',
			modulename: 'ddii_scopus.src.parsers_pack',
			qualname: 'LineEditPack',
			kind: 'class',
			doc: '<p>\u0418\u0437\u0432\u043b\u0435\u043a\u0430\u0435\u0442 \u0432\u0441\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f \u0438\u0437 lineobj_txt \u0438 \u0443\u043f\u0430\u043a\u043e\u0432\u044b\u0432\u0430\u0435\u0442 \u0438\u0445 \u0432 list[int] \u0434\u043b\u044f \u043e\u0442\u043f\u0440\u0430\u0432\u043a\u0438 \u043f\u043e \u043c\u043e\u0434\u0431\u0430\u0441</p>\n\n<p>ln_objects: list[LineObj] - \u0441\u043f\u0438\u0441\u043e\u043a \u043e\u0431\u044a\u0435\u043a\u0442\u043e\u0432 QLineEdit</p>\n\n<p>endian: str - \u0444\u043e\u0440\u043c\u0430\u0442 \u0442\u0430\u043a\u043e\u0439 \u0436\u0435 \u043a\u0430\u043a struct "little", "big"</p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer',
			modulename: 'ddii_scopus.src.plot_renderer',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.src_path',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'src_path',
			kind: 'variable',
			doc: '<p></p>\n',
			default_value: 'PosixPath(&#x27;/Users/vladk/git&#x27;)',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.GraphPen',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'GraphPen',
			kind: 'class',
			doc: '<p>\u041e\u0442\u0440\u0438\u0441\u043e\u0432\u0449\u0438\u043a \u0433\u0440\u0430\u0444\u0438\u043a\u043e\u0432</p>\n\n<p>\u0414\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u0432 layout \u043e\u043a\u043d\u043e \u0433\u0440\u0430\u0444\u0438\u043a\u0430 \u0438 \u043e\u0442\u0440\u0438\u0441\u043e\u0432\u044b\u0432\u0435\u0442 \u0433\u0440\u0430\u0444\u0438\u043a</p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.GraphPen.__init__',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'GraphPen.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">layout</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QHBoxLayout</span> <span class="o">|</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QVBoxLayout</span> <span class="o">|</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QGridLayout</span>,</span><span class="param">\t<span class="n">name</span><span class="p">:</span> <span class="nb">str</span> <span class="o">=</span> <span class="s1">&#39;default_graph&#39;</span>,</span><span class="param">\t<span class="n">color</span><span class="p">:</span> <span class="nb">tuple</span> <span class="o">=</span> <span class="p">(</span><span class="mi">255</span><span class="p">,</span> <span class="mi">120</span><span class="p">,</span> <span class="mi">10</span><span class="p">)</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.GraphPen.plt_widget',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'GraphPen.plt_widget',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.GraphPen.pen',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'GraphPen.pen',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.GraphPen.name_frame',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'GraphPen.name_frame',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': str',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.GraphPen.plot_item',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'GraphPen.plot_item',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.GraphPen.draw_graph',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'GraphPen.draw_graph',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="bp">self</span>,</span><span class="param">\t<span class="n">data</span><span class="p">:</span> <span class="nb">list</span>,</span><span class="param">\t<span class="n">name_file_save_data</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">str</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span>,</span><span class="param">\t<span class="n">name_data</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">str</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span>,</span><span class="param">\t<span class="n">path_to_save</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="n">pathlib</span><span class="o">.</span><span class="n">Path</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span>,</span><span class="param">\t<span class="n">save_log</span><span class="o">=</span><span class="kc">False</span>,</span><span class="param">\t<span class="n">clear</span><span class="o">=</span><span class="kc">False</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen',
			kind: 'class',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.__init__',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">layout</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QHBoxLayout</span> <span class="o">|</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QVBoxLayout</span> <span class="o">|</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QGridLayout</span>,</span><span class="param">\t<span class="n">name</span><span class="p">:</span> <span class="nb">str</span>,</span><span class="param">\t<span class="n">color</span><span class="p">:</span> <span class="nb">tuple</span> <span class="o">=</span> <span class="p">(</span><span class="mi">0</span><span class="p">,</span> <span class="mi">0</span><span class="p">,</span> <span class="mi">255</span><span class="p">,</span> <span class="mi">150</span><span class="p">)</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.hist_widget',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.hist_widget',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': pyqtgraph.widgets.PlotWidget.PlotWidget',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.color',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.color',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.pen',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.pen',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.outline_pen',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.outline_pen',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.name_frame',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.name_frame',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': str',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.hist_item',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.hist_item',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.hist_outline_item',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.hist_outline_item',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.accumulate_data',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.accumulate_data',
			kind: 'variable',
			doc: '<p></p>\n',
			annotation: ': list',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.padding_factor',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.padding_factor',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.bin_count',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.bin_count',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.x_range',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.x_range',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.bins',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.bins',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.hist_clear',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.hist_clear',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.plot_renderer.HistPen.draw_hist',
			modulename: 'ddii_scopus.src.plot_renderer',
			qualname: 'HistPen.draw_hist',
			kind: 'function',
			doc: '<p>\u041e\u0442\u0440\u0438\u0441\u043e\u0432\u044b\u0432\u0430\u0435\u0442 \u0433\u0438\u0441\u0442\u043e\u0433\u0440\u0430\u043c\u043c\u0443 \u0434\u0430\u043d\u043d\u044b\u0445 \u0441 \u0432\u043e\u0437\u043c\u043e\u0436\u043d\u043e\u0441\u0442\u044c\u044e \u0444\u0438\u043b\u044c\u0442\u0440\u0430\u0446\u0438\u0438 \u0438 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f\nArgs:\n    data: \u0421\u043f\u0438\u0441\u043e\u043a \u0447\u0438\u0441\u043b\u043e\u0432\u044b\u0445 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0439 \u0434\u043b\u044f \u043f\u043e\u0441\u0442\u0440\u043e\u0435\u043d\u0438\u044f \u0433\u0438\u0441\u0442\u043e\u0433\u0440\u0430\u043c\u043c\u044b\n    filtr: \u0424\u0443\u043d\u043a\u0446\u0438\u044f \u0444\u0438\u043b\u044c\u0442\u0440\u0430\u0446\u0438\u0438 \u0434\u0430\u043d\u043d\u044b\u0445 (\u0435\u0441\u043b\u0438 None, \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f \u043c\u0430\u043a\u0441\u0438\u043c\u0443\u043c)\n    save_log: \u0424\u043b\u0430\u0433 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f \u0434\u0430\u043d\u043d\u044b\u0445\n    name_file_save_data: \u0418\u043c\u044f \u0444\u0430\u0439\u043b\u0430 \u0434\u043b\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f</p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="bp">self</span>,</span><span class="param">\t<span class="n">data</span><span class="p">:</span> <span class="n">Sequence</span><span class="p">[</span><span class="n">Union</span><span class="p">[</span><span class="nb">int</span><span class="p">,</span> <span class="nb">float</span><span class="p">]]</span>,</span><span class="param">\t<span class="n">name_file_save_data</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">str</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span>,</span><span class="param">\t<span class="n">name_data</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">str</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span>,</span><span class="param">\t<span class="nb">filter</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="n">Callable</span><span class="p">]</span> <span class="o">=</span> <span class="kc">None</span>,</span><span class="param">\t<span class="n">save_log</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">bool</span><span class="p">]</span> <span class="o">=</span> <span class="kc">False</span>,</span><span class="param">\t<span class="n">clear</span><span class="p">:</span> <span class="n">Optional</span><span class="p">[</span><span class="nb">bool</span><span class="p">]</span> <span class="o">=</span> <span class="kc">False</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'async def',
		},
		{
			fullname: 'ddii_scopus.src.print_logger',
			modulename: 'ddii_scopus.src.print_logger',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.print_logger.PrintLogger',
			modulename: 'ddii_scopus.src.print_logger',
			qualname: 'PrintLogger',
			kind: 'class',
			doc: '<p>\u0417\u0430\u043c\u0435\u043d\u044f\u0435\u0442 \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u044b\u0439 \u043b\u043e\u0433\u0433\u0435\u0440, \u0438\u043c\u0438\u0442\u0438\u0440\u0443\u044f \u0435\u0433\u043e \u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441</p>\n',
		},
		{
			fullname: 'ddii_scopus.src.py_toggle',
			modulename: 'ddii_scopus.src.py_toggle',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.py_toggle.pyToggle',
			modulename: 'ddii_scopus.src.py_toggle',
			qualname: 'pyToggle',
			kind: 'class',
			doc: '<p>QCheckBox(parent: Optional[QWidget] = None)\nQCheckBox(text: Optional[str], parent: Optional[QWidget] = None)</p>\n',
			bases: 'PyQt6.QtWidgets.QCheckBox',
		},
		{
			fullname: 'ddii_scopus.src.py_toggle.pyToggle.__init__',
			modulename: 'ddii_scopus.src.py_toggle',
			qualname: 'pyToggle.__init__',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">width</span><span class="o">=</span><span class="mi">60</span>,</span><span class="param">\t<span class="n">bg_color</span><span class="o">=</span><span class="s1">&#39;#f8f8f8&#39;</span>,</span><span class="param">\t<span class="n">circle_color</span><span class="o">=</span><span class="s1">&#39;#DDD&#39;</span>,</span><span class="param">\t<span class="n">active_color</span><span class="o">=</span><span class="s1">&#39;#32c75a&#39;</span>,</span><span class="param">\t<span class="n">border_color</span><span class="o">=</span><span class="s1">&#39;#b9b9b9&#39;</span>,</span><span class="param">\t<span class="n">circle_active_color</span><span class="o">=</span><span class="s1">&#39;#f8f8f8&#39;</span>,</span><span class="param">\t<span class="n">animation_curve</span><span class="o">=&lt;</span><span class="n">Type</span><span class="o">.</span><span class="n">OutBounce</span><span class="p">:</span> <span class="mi">38</span><span class="o">&gt;</span></span>)</span>',
		},
		{
			fullname: 'ddii_scopus.src.py_toggle.pyToggle.circle_active_color',
			modulename: 'ddii_scopus.src.py_toggle',
			qualname: 'pyToggle.circle_active_color',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.py_toggle.pyToggle.animation',
			modulename: 'ddii_scopus.src.py_toggle',
			qualname: 'pyToggle.animation',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.py_toggle.pyToggle.circle_position',
			modulename: 'ddii_scopus.src.py_toggle',
			qualname: 'pyToggle.circle_position',
			kind: 'variable',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.py_toggle.pyToggle.start_transition',
			modulename: 'ddii_scopus.src.py_toggle',
			qualname: 'pyToggle.start_transition',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">value</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.py_toggle.pyToggle.hitButton',
			modulename: 'ddii_scopus.src.py_toggle',
			qualname: 'pyToggle.hitButton',
			kind: 'function',
			doc: '<p>hitButton(self, pos: QPoint) -> bool</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">pos</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtCore</span><span class="o">.</span><span class="n">QPoint</span></span><span class="return-annotation">) -> <span class="nb">bool</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.py_toggle.pyToggle.paintEvent',
			modulename: 'ddii_scopus.src.py_toggle',
			qualname: 'pyToggle.paintEvent',
			kind: 'function',
			doc: '<p>paintEvent(self, a0: Optional[QPaintEvent])</p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="bp">self</span>, </span><span class="param"><span class="n">e</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.signal_manager',
			modulename: 'ddii_scopus.src.signal_manager',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.write_data_to_file',
			modulename: 'ddii_scopus.src.write_data_to_file',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.write_data_to_file.writer_graph_data',
			modulename: 'ddii_scopus.src.write_data_to_file',
			qualname: 'writer_graph_data',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">x</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span> <span class="o">|</span> <span class="nb">float</span><span class="p">]</span>,</span><span class="param">\t<span class="n">y</span><span class="p">:</span> <span class="nb">list</span><span class="p">[</span><span class="nb">int</span> <span class="o">|</span> <span class="nb">float</span><span class="p">]</span>,</span><span class="param">\t<span class="n">name</span><span class="p">:</span> <span class="nb">str</span>,</span><span class="param">\t<span class="n">folder_path</span><span class="p">:</span> <span class="n">pathlib</span><span class="o">.</span><span class="n">Path</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.write_data_to_file.write_to_hdf5_file',
			modulename: 'ddii_scopus.src.write_data_to_file',
			qualname: 'write_to_hdf5_file',
			kind: 'function',
			doc: '<p>_summary_</p>\n\n<p>Args:\n    data (list): \u041c\u0430\u0441\u0441\u0438\u0432 \u043b\u044e\u0431\u043e\u0439 \u0440\u0430\u0437\u043c\u0435\u0440\u043d\u043e\u0441\u0442\u0438, \u0432\u0430\u0436\u043d\u043e!!! \u0434\u0430\u043d\u043d\u044b\u0435 \u0432 \u043c\u0430\u0441\u0438\u0432\u0435 \u043e\u0431\u044a\u0435\u0434\u0435\u043d\u0435\u043d\u044b \u043f\u043e \u043a\u043e\u043b\u043b\u043e\u043d\u043a\u0430\u043c\n    name_grpup (str): \u0412 hdf5 \u0434\u0430\u043d\u043d\u044b\u0435 \u043e\u0431\u0435\u0434\u0435\u043d\u0435\u043d\u044b \u043f\u043e\u0434 \u043e\u0434\u043d\u0438\u043c \u043b\u0435\u0439\u0431\u043b\u043e\u043c\n    path_hdf5 (Path): \u041a\u0443\u0434\u0430 \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0442\u044c hdf5\n    name_file_hdf5 (str): \u041f\u043e\u0434 \u043a\u0430\u043a\u0438\u043c \u0438\u043c\u0435\u043d\u0435\u043c \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0442\u044c hdf5\n    loc (bool, optional): \u0415\u0441\u043b\u0438 True, \u0442\u043e data \u0431\u0443\u0434\u0435\u0442 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430 \u043a\u0430\u043a \u0441\u0442\u0440\u043e\u043a\u0430 \u0432 \u0432\u0438\u0434\u0435 1,22\n    \u041d\u0443\u0436\u043d\u043e \u0434\u043b\u044f \u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u0438 \u0441 Veusz \u0438 xcel.</p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">data</span><span class="p">:</span> <span class="nb">list</span>,</span><span class="param">\t<span class="n">name_group</span><span class="p">:</span> <span class="nb">str</span>,</span><span class="param">\t<span class="n">path_hdf5</span><span class="p">:</span> <span class="n">pathlib</span><span class="o">.</span><span class="n">Path</span>,</span><span class="param">\t<span class="n">name_file_hdf5</span><span class="p">:</span> <span class="nb">str</span>,</span><span class="param">\t<span class="n">name_data</span><span class="p">:</span> <span class="nb">str</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.write_data_to_file.read_hdf5_file',
			modulename: 'ddii_scopus.src.write_data_to_file',
			qualname: 'read_hdf5_file',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">file_path_hdf5</span><span class="p">:</span> <span class="n">pathlib</span><span class="o">.</span><span class="n">Path</span>, </span><span class="param"><span class="n">name_group</span><span class="p">:</span> <span class="nb">str</span></span><span class="return-annotation">):</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.write_data_to_file.hdf5_to_csv',
			modulename: 'ddii_scopus.src.write_data_to_file',
			qualname: 'hdf5_to_csv',
			kind: 'function',
			doc: '<p>\u041f\u0440\u0435\u043e\u0431\u0440\u0430\u0437\u0443\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0435 \u0438\u0437 HDF5-\u0444\u0430\u0439\u043b\u0430 \u0432 \u0442\u0435\u043a\u0441\u0442\u043e\u0432\u044b\u0435 \u0444\u0430\u0439\u043b\u044b.</p>\n\n<h6 id="parameters">Parameters</h6>\n\n<ul>\n<li><strong>path_hdf5_file</strong>:  \u041f\u0443\u0442\u044c \u043a HDF5-\u0444\u0430\u0439\u043b\u0443</li>\n</ul>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">path_hdf5_file</span><span class="p">:</span> <span class="n">pathlib</span><span class="o">.</span><span class="n">Path</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.write_data_to_file.hdf5_converter',
			modulename: 'ddii_scopus.src.write_data_to_file',
			qualname: 'hdf5_converter',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="param"><span class="n">path_to_folder</span><span class="p">:</span> <span class="n">pathlib</span><span class="o">.</span><span class="n">Path</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.ww_maker',
			modulename: 'ddii_scopus.src.ww_maker',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.src.ww_maker.init_widgets',
			modulename: 'ddii_scopus.src.ww_maker',
			qualname: 'init_widgets',
			kind: 'function',
			doc: '<p>\u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u043e\u043a\u043d\u0430 \u0438\u0437 \u043c\u0430\u043a\u0435\u0442\u043e\u0432 \u0432\u0438\u0434\u0436\u0435\u0442\u043e\u0432</p>\n\n<p>Args:\n    w_graph_widget (GraphWidget): -\n    gridLayout_main_split (QGridLayout): \u0433\u043b\u0430\u0432\u043d\u044b\u0439 \u043b\u0430\u0439\u043e\u0443\u0442 \u0434\u043b\u044f \u0432\u0438\u0434\u0436\u0435\u0442\u043e\u0432\n    widget_model (dict): \u0421\u043b\u043e\u0432\u0430\u0440\u044c \u0441\u043b\u043e\u0432\u0430\u0440\u0435\u0439 \u0432\u0438\u0434\u0436\u0435\u0442\u043e\u0432 dict{"\u0412\u043a\u043b\u0430\u0434\u043a\u0438 \u0442\u0430\u0431 \u0432\u0438\u0434\u0436\u0435\u0442\u043e\u0432": dict{"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0432\u0438\u0434\u0436\u0435\u0442\u043e\u0432": \u0412\u0438\u0434\u0436\u0435\u0442\u044b Object}}</p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">w_graph_widget</span>,</span><span class="param">\t<span class="n">gridLayout_main_split</span><span class="p">:</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QGridLayout</span>,</span><span class="param">\t<span class="n">widget_model</span><span class="p">:</span> <span class="n">Dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="n">Dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QWidget</span><span class="p">]]</span></span><span class="return-annotation">) -> <span class="kc">None</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.src.ww_maker.create_tab_widget_items',
			modulename: 'ddii_scopus.src.ww_maker',
			qualname: 'create_tab_widget_items',
			kind: 'function',
			doc: '<p>\u0421\u043e\u0437\u0434\u0430\u0435\u0442 QTabWidget \u0441 \u0432\u043a\u043b\u0430\u0434\u043a\u0430\u043c\u0438, \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u044f \u0432\u0441\u0435 \u0432\u043a\u043b\u0430\u0434\u043a\u0438 \u0447\u0435\u0440\u0435\u0437 \u0444\u0430\u0431\u0440\u0438\u043a\u0443.</p>\n',
			signature:
				'<span class="signature pdoc-code multiline">(<span class="param">\t<span class="n">widget_model</span><span class="p">:</span> <span class="n">Dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="n">Dict</span><span class="p">[</span><span class="nb">str</span><span class="p">,</span> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QWidget</span><span class="p">]]</span></span><span class="return-annotation">) -> <span class="n">PyQt6</span><span class="o">.</span><span class="n">QtWidgets</span><span class="o">.</span><span class="n">QTabWidget</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.style',
			modulename: 'ddii_scopus.style',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.style.styleSheet',
			modulename: 'ddii_scopus.style.styleSheet',
			kind: 'module',
			doc: '<p></p>\n',
		},
		{
			fullname: 'ddii_scopus.style.styleSheet.widget_led_on',
			modulename: 'ddii_scopus.style.styleSheet',
			qualname: 'widget_led_on',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="return-annotation">) -> <span class="nb">str</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.style.styleSheet.widget_led_off',
			modulename: 'ddii_scopus.style.styleSheet',
			qualname: 'widget_led_off',
			kind: 'function',
			doc: '<p></p>\n',
			signature:
				'<span class="signature pdoc-code condensed">(<span class="return-annotation">) -> <span class="nb">str</span>:</span></span>',
			funcdef: 'def',
		},
		{
			fullname: 'ddii_scopus.to_exe',
			modulename: 'ddii_scopus.to_exe',
			kind: 'module',
			doc: '<p></p>\n',
		},
	]

	// mirrored in build-search-index.js (part 1)
	// Also split on html tags. this is a cheap heuristic, but good enough.
	elasticlunr.tokenizer.setSeperator(/[\s\-.;&_'"=,()]+|<[^>]*>/)

	let searchIndex
	if (docs._isPrebuiltIndex) {
		console.info('using precompiled search index')
		searchIndex = elasticlunr.Index.load(docs)
	} else {
		console.time('building search index')
		// mirrored in build-search-index.js (part 2)
		searchIndex = elasticlunr(function () {
			this.pipeline.remove(elasticlunr.stemmer)
			this.pipeline.remove(elasticlunr.stopWordFilter)
			this.addField('qualname')
			this.addField('fullname')
			this.addField('annotation')
			this.addField('default_value')
			this.addField('signature')
			this.addField('bases')
			this.addField('doc')
			this.setRef('fullname')
		})
		for (let doc of docs) {
			searchIndex.addDoc(doc)
		}
		console.timeEnd('building search index')
	}

	return term =>
		searchIndex.search(term, {
			fields: {
				qualname: { boost: 4 },
				fullname: { boost: 2 },
				annotation: { boost: 2 },
				default_value: { boost: 2 },
				signature: { boost: 2 },
				bases: { boost: 2 },
				doc: { boost: 1 },
			},
			expand: true,
		})
})()

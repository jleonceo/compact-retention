# Seis pasos con el fallo que enseñó cada uno

> Esto vivía dentro del README y son dos documentos con dos lectores distintos. Quien sufre
> auto-compacts quiere la herramienta; quien quiera copiar la forma de medir, esto. Los resultados
> están en [README.md](README.md).

### Cómo se midió: la parte reutilizable

Lo de arriba son los resultados. Esto es cómo se consiguieron. El orden de los pasos importa
más que la herramienta. Se puede copiar en cualquier medición parecida. Fueron tres días. Dos y medio
de ellos se fueron en medir en vez de en configurar.

**1. Instrumentar antes de tocar nada.** Un hook que se dispara en el corte y sella el transcript
entero más el estado de git. Sin eso, cada compact es un suceso del que solo queda una impresión.
La lección vino por las malas: el primer auto-compact **interrumpió literalmente la instalación del
instrumento que debía medirlo**, entró 55,9 segundos antes de que el hook quedara registrado, y su
bitácora vacía se leyó como «no ha ocurrido». De ahí sale una regla que vale para cualquier
instrumento: si nació después de la ventana que dice cubrir, **su silencio no es evidencia**.

**2. Una sola vara para todos los casos.** Las cinco primeras medidas se hicieron cada una a su
manera. Una contaba ficheros escritos que el resumen nombra; otra, ficheros sin commitear que el
resumen nombra. Puestas en fila dibujaban un desplome que no existía. Cifra bien calculada sobre
objeto distinto sigue siendo falsa y encima con aire de rigor.

**3. Escribir la predicción antes de ver el resultado.** Antes de subir el umbral se dejó escrito
dónde tenía que caer el corte: entre 585.000 y 600.000 tokens. Cayó en 580.370, o sea que **la
predicción falló por un 0,8 %** y quedó escrita en su sitio. Una predicción que se ajusta después de
ver el dato no es una predicción.

**4. Refutar la hipótesis rival antes de celebrar la propia.** Existe un mecanismo documentado que,
de estar actuando aquí, habría invalidado el trabajo entero: uno que recorta el contexto al llegar
al 90 % de ocupación. Se descartó con dato propio. El argumento importa entero: los cortes no
caían a un porcentaje cualquiera, sino **en la ventana menos un margen**, que es la
firma de un umbral por buffer y no la de ese mecanismo. Con la mitad del argumento (el 90 % contra
el 98,7 %) la conclusión ni siquiera se sostiene.

**5. Publicar la corrección encima de la versión anterior, sin borrarla.** Con siete ventanas medidas
la conclusión era que el resumen tiene un techo fijo de nueve a diecisiete nombres, pasara lo que
pasara. Se ensanchó a diez-veinte al llegar la octava ventana, y con diecinueve se cayó del todo:
cuatro pasaban de diecisiete, dos de ellas con 21 y 28. Con veintiséis, la variable que manda
resultó ser la densidad. La tesis del techo estaba escrita y publicada. Sigue escrita al
lado de lo que la corrige, porque un registro que borra sus versiones anteriores no enseña cómo se
corrige una medición.

**6. Un baseline que se está midiendo no admite dos ejecuciones a la vez.** El error más caro de la
serie casi no se ve: un proceso de fondo que no imprime nada no está parado, así que se relanzó y
los dos quedaron vivos escribiendo el mismo fichero de referencia. En medio se cambió el código bajo
medición. El segundo habría sobrescrito el «antes» con cifras del «después», el diff habría salido
plano y **nada lo habría delatado**: dos ficheros con el nombre correcto y el contenido
intercambiado no disparan ninguna alarma. Se cazó mirando los procesos por otro motivo.

---

# Six steps with the failure that taught each one

Everything above is results. This is how they were reached. The order of the steps matters
more than the tool does. It transfers to any similar measurement. It took three days, two and a
half of them spent measuring rather than configuring.

**1. Instrument before touching anything.** A hook that fires on the cut and seals the whole
transcript plus the git state. Without that, each compact is an event you only have an impression
of. The lesson came the hard way: the first auto-compact **literally interrupted the installation of
the instrument meant to measure it**, landing 55.9 seconds before the hook was registered, and its
empty log was read as "it never happened". Hence a rule that holds for any instrument: if it was
born after the window it claims to cover, **its silence is not evidence**.

**2. One yardstick for every case.** The first five measurements were each done their own way. One
counted written files named by the summary; another, uncommitted files named by the summary. Lined
up, they drew a collapse that did not exist. A figure computed correctly over a different object is
still false, with an air of rigour on top.

**3. Write the prediction before seeing the result.** Before raising the threshold, where the cut
had to land was written down: between 585,000 and 600,000 tokens. It landed at 580,370, so **the
prediction missed by 0.8 %**. It stayed on the record. A prediction adjusted after seeing the
data is not a prediction.

**4. Refute the rival hypothesis before celebrating your own.** A documented mechanism exists that,
had it been active here, would have invalidated the whole effort: one that trims context at 90 %
occupancy. It was ruled out with local data, and the argument matters in full: the cuts did not land
at some arbitrary percentage but **at the window minus a margin**, which is the
signature of a buffer threshold and not of that mechanism. With half the argument (90 % versus
98.7 %) the conclusion does not even hold.

**5. Publish the correction on top of the earlier version, without deleting it.** With seven windows
measured, the conclusion was that the summary has a fixed ceiling of nine to seventeen names, no
matter what. It widened to ten-twenty when the eighth window arrived, and with nineteen it fell for
good: four went past seventeen, two of them keeping 21 and 28. With twenty-six, the variable that
rules turned out to be density. The ceiling claim was written and published. It still sits next
to what corrects it, because a record that deletes its earlier versions cannot teach how a
measurement gets corrected.

**6. A baseline being measured does not allow two runs at once.** The costliest mistake in the
series is nearly invisible: a background process printing nothing is not a stalled process, so it
got relaunched, and both stayed alive writing the same reference file. Meanwhile the code under
measurement was changed. The second run would have overwritten the "before" with "after" figures,
the diff would have come out flat, and **nothing would have flagged it**: two files with the right
names and swapped contents raise no alarm. It was caught while looking at processes for an
unrelated reason.

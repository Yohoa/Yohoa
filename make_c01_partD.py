#!/usr/bin/env python3
"""Append part D of bilingual C01: References and closing tags."""
out = open('Healing_Bilingual/ops/xhtml/C01_chapter.xhtml', 'a', encoding='utf-8')
out.write('''\
<h3 class="h3">References</h3>
<p class="ref">Bromberg, P. (2011). <em>The shadow of the tsunami and the growth of the relational mind</em>. New York: Taylor &amp; Francis.</p>
<p class="ref">Gazzaniga, M. S. (1985). <em>The social brain: discovering the networks of the mind</em>. New York: Basic Books.</p>
<p class="ref">Hanson, R. (2014). <em>Hardwiring happiness: the new brain science of contentment, calm, and confidence</em>. New York: Harmony Publications.</p>
<p class="ref">Herman, J. L. (1992) <em>Trauma and recovery</em>. New York: Basic Books.</p>
<p class="ref">Ogden, P. &amp; Fisher, J. (2015). <em>Sensorimotor psychotherapy: interventions for trauma and attachment</em>. New York: W.W. Norton.</p>
<p class="ref">Ogden, P., Minton, K. &amp; Pain, C. (2006). <em>Trauma and the body: a sensorimotor approach to psychotherapy</em>. New York: W.W. Norton.</p>
<p class="ref">Pollack, S.M., Padulla, T., &amp; Seigel, R.D. (2014). <em>Sitting together: essential skills for mindfulness-based psychotherapy</em>. New York: Guilford Press.</p>
<p class="ref">Porges, S.W. (2011). <em>The Polyvagal theory: neurophysiological foundations of emotions, attachment, communication, and self-regulation</em>. New York: W.W. Norton.</p>
<p class="ref">Schwartz, R. (1995). <em>Internal family systems therapy</em>. New York: Guilford Press.</p>
<p class="ref">Schwartz, R. (2001). <em>Introduction to the internal family systems model</em>. Oak Park, IL: Trailhead Publications.</p>
<p class="ref">Siegel, D.J. (1999). <em>The developing mind: toward a neurobiology of interpersonal experience</em>. New York: Guilford Press.</p>
<p class="ref">Siegel, D. J. (2010). <em>The neurobiology of &#8216;we.&#8217;</em> Keynote address, Psychotherapy Networker Symposium, Washington, D.C., March 2010.</p>
<p class="ref">Van der Hart, O., Nijenhuis, E.R.S., &amp; Steele, K. (2006). <em>The haunted self: structural dissociation and the treatment of chronic traumatization</em>. New York: W.W. Norton.</p>
<p class="ref">Van der Hart, O., Nijenhuis, E.R.S., Steele, K., &amp; Brown, D. (2004). Trauma-related dissociation: conceptual clarity lost and found. <em>Australian and New Zealand Journal of Psychiatry</em>, 38, 906&#8211;914.</p>
<p class="ref">Van der Hart, O., van Dijke, A., van Son, M., and Steele, K. (2000). Somatoform dissociation in traumatized World War I combat soldiers: a neglected clinical heritage. <em>Journal of Trauma and Dissociation</em>, 1(4), 33&#8211;66.</p>
<p class="ref">Van der Kolk, B.A. (2014). <em>The body keeps the score: brain, mind and body in the healing of trauma</em>. New York: Viking Press.</p>
</section>
</body>
</html>
''')
out.close()
print("Part D written.")

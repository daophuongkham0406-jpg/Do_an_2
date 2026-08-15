import re


PHRASE_REPLACEMENTS = [
    (r"\bfor the desired reps\b", "theo số lần được chỉ định"),
    (r"\bfor the desired number of reps\b", "theo số lần được chỉ định"),
    (r"\band body level\b", "và giữ thân người cân bằng"),
    (r"\bbrace (your|the) core\b", "siết chặt cơ bụng"),
    (r"\bkeep your core tight\b", "giữ thân giữa chắc"),
    (r"\blower yourself under control\b", "hạ người xuống có kiểm soát"),
    (r"\blower (it|them|the weight) under control\b", "hạ tạ xuống có kiểm soát"),
    (r"\bpress back up to the start position\b", "đẩy người trở lại vị trí ban đầu"),
    (r"\brepeat for the desired number of reps\b", "lặp lại theo số lần được chỉ định"),
    (r"\brepeat\b", "lặp lại động tác"),
    (r"\bswitch sides and repeat\b", "đổi bên và lặp lại"),
    (r"\bhold for 20 to 30 seconds, breathing steadily\b", "giữ 20-30 giây và thở đều"),
    (r"\bbreathing steadily\b", "thở đều"),
    (r"\bpalms facing away\b", "lòng bàn tay hướng ra ngoài"),
    (r"\bshoulder-width apart\b", "rộng bằng vai"),
    (r"\bslightly wider than shoulders\b", "rộng hơn vai một chút"),
    (r"\bwith arms straight\b", "với tay duỗi thẳng"),
    (r"\buntil your body is straight\b", "đến khi cơ thể thẳng lại"),
    (r"\bdrive your elbows down\b", "kéo khuỷu tay xuống"),
    (r"\bmaintain power output\b", "duy trì lực ổn định"),
    (r"\bcontinue for the desired duration or distance\b", "tiếp tục theo thời lượng hoặc quãng đường được chỉ định"),
]


STEP_PATTERNS = [
    (r"^start in a high plank position\.?$", "Bắt đầu ở tư thế plank cao, hai tay chống dưới vai và thân người tạo thành một đường thẳng."),
    (r"^drive one knee toward your chest\.?$", "Kéo một gối về phía ngực trong khi vẫn giữ thân người ổn định."),
    (r"^quickly switch legs, driving the other knee forward\.?$", "Nhanh chóng đổi chân, kéo gối còn lại về phía trước."),
    (r"^continue alternating at a brisk pace\.?$", "Tiếp tục luân phiên hai chân với nhịp nhanh nhưng vẫn kiểm soát kỹ thuật."),
    (r"^switch sides and repeat\.?$", "Đổi bên và lặp lại động tác."),
    (r"^repeat for the desired number of reps\.?$", "Lặp lại theo số lần được chỉ định."),
    (r"^repeat for the desired reps\.?$", "Lặp lại theo số lần được chỉ định."),
    (r"^repeat on both sides\.?$", "Lặp lại cho cả hai bên."),
    (r"^repeat\.?$", "Lặp lại động tác."),
    (r"^kneel on the floor and grip the ab wheel handles shoulder-width\.?$", "Quỳ trên sàn và nắm hai tay cầm bánh xe rộng bằng vai."),
    (r"^roll the wheel slowly forward, extending the body as far as you can control\.?$", "Lăn bánh xe chậm về phía trước, duỗi người xa nhất trong phạm vi còn kiểm soát được."),
    (r"^stop before the hips sag or the back arches\.?$", "Dừng lại trước khi hông bị võng hoặc lưng bị ưỡn quá mức."),
    (r"^pull the wheel back to the knees by contracting the abs\.?$", "Co cơ bụng để kéo bánh xe trở lại gần đầu gối."),
    (r"^sit on the air bike and grip the moving handles\.?$", "Ngồi lên xe đạp gió và nắm hai tay cầm chuyển động."),
    (r"^place your feet on the pedals and brace your core\.?$", "Đặt chân lên bàn đạp và siết chặt cơ bụng."),
    (r"^push and pull the handles while pedaling at a steady pace\.?$", "Đẩy và kéo tay cầm đồng thời đạp xe với nhịp ổn định."),
    (r"^drive with both arms and legs to maintain power output\.?$", "Dùng cả tay và chân để duy trì lực đều."),
    (r"^grip the bar wider than shoulder width with palms facing away\.?$", "Nắm thanh xà rộng hơn vai, lòng bàn tay hướng ra ngoài."),
    (r"^pull yourself up while shifting your body toward one hand\.?$", "Kéo người lên đồng thời chuyển trọng tâm về một bên tay."),
    (r"^keep the opposite arm straight as a support\.?$", "Giữ tay còn lại tương đối thẳng để hỗ trợ."),
    (r"^alternate sides each rep or complete reps on one side first\.?$", "Luân phiên hai bên mỗi lần lặp hoặc hoàn thành một bên trước."),
    (r"^set up in a wide push-up position with arms straight\.?$", "Vào tư thế chống đẩy rộng tay, hai tay duỗi thẳng."),
    (r"^lower yourself toward one hand while keeping the other arm straight\.?$", "Hạ người về một bên tay, tay còn lại giữ thẳng để hỗ trợ."),
    (r"^press back up to the start position\.?$", "Đẩy người trở lại vị trí ban đầu."),
    (r"^hold a pair of dumbbells at shoulder height with palms facing you\.?$", "Giữ hai tạ đơn ngang vai, lòng bàn tay hướng vào người."),
    (r"^press the dumbbells overhead while rotating your palms to face forward\.?$", "Đẩy tạ lên qua đầu đồng thời xoay lòng bàn tay hướng về phía trước."),
    (r"^fully extend your arms at the top without locking the elbows\.?$", "Duỗi tay ở vị trí trên cùng nhưng không khóa cứng khuỷu tay."),
    (r"^reverse the motion and rotate back to the start\.?$", "Đảo ngược chuyển động và xoay tay về vị trí ban đầu."),
    (r"^place your knees on the assisted pull-up machine pad\.?$", "Đặt hai gối lên đệm hỗ trợ của máy kéo xà."),
    (r"^grip the bar with palms facing away, slightly wider than shoulders\.?$", "Nắm thanh xà rộng hơn vai một chút, lòng bàn tay hướng ra ngoài."),
    (r"^pull your chest toward the bar by driving your elbows down\.?$", "Kéo ngực hướng về thanh xà bằng cách kéo khuỷu tay xuống."),
    (r"^lower yourself under control to a full hang\.?$", "Hạ người xuống có kiểm soát đến tư thế treo thẳng tay."),
    (r"^lie face down on a hyperextension bench with hips at the pad edge\.?$", "Nằm sấp trên ghế hyperextension, đặt hông sát mép đệm."),
    (r"^lower your upper body toward the floor\.?$", "Hạ thân trên xuống hướng về phía sàn có kiểm soát."),
    (r"^raise your torso back up until your body is straight\.?$", "Nâng thân trên trở lại đến khi cơ thể thẳng."),
    (r"^stand holding a barbell with arms straight in front of your thighs\.?$", "Đứng thẳng, giữ thanh tạ phía trước đùi với hai tay duỗi gần thẳng."),
    (r"^stand holding dumbbells at your sides with palms facing in\.?$", "Đứng thẳng, giữ tạ đơn hai bên thân người, lòng bàn tay hướng vào trong."),
    (r"^hold the bar with an overhand grip\.?$", "Nắm thanh tạ bằng kiểu nắm sấp."),
    (r"^hold an ez bar with a shoulder-width grip\.?$", "Nắm thanh EZ rộng bằng vai."),
    (r"^keep core braced and body level\.?$", "Siết cơ bụng và giữ thân người cân bằng."),
    (r"^hold the top position briefly\.?$", "Giữ ngắn ở vị trí trên cùng."),
    (r"^pause briefly at the top\.?$", "Dừng ngắn ở vị trí trên cùng."),
    (r"^squeeze at the top\.?$", "Siết cơ ở vị trí trên cùng."),
    (r"^stand in front of a low cable pulley\.?$", "Đứng trước ròng rọc cáp thấp."),
    (r"^attach a single handle to the low pulley\.?$", "Gắn tay cầm đơn vào ròng rọc thấp."),
    (r"^anchor the ropes to a fixed point and grab one end in each hand\.?$", "Cố định dây thừng vào điểm neo chắc chắn và cầm mỗi tay một đầu dây."),
    (r"^step back so the ropes have moderate slack\.?$", "Bước lùi lại để dây có độ chùng vừa phải."),
    (r"^drop into a quarter squat with feet shoulder-width\.?$", "Hạ người vào tư thế squat một phần tư, hai chân rộng bằng vai."),
    (r"^drive each arm up and down rapidly to send waves through the ropes\.?$", "Đánh hai tay lên xuống nhanh và mạnh để tạo sóng trên dây."),
    (r"^continue for the prescribed work interval\.?$", "Tiếp tục trong khoảng thời gian tập được chỉ định."),
    (r"^continue alternating for the desired number of reps\.?$", "Tiếp tục luân phiên hai bên theo số lần được chỉ định."),
    (r"^curl the bar up toward your shoulders\.?$", "Cuốn thanh tạ lên về phía vai, giữ khuỷu tay gần thân người."),
    (r"^drive through your front heel to return to standing\.?$", "Đạp mạnh qua gót chân trước để đứng thẳng trở lại."),
    (r"^squeeze at the top, then lower under control\.?$", "Siết cơ ở vị trí trên cùng rồi hạ xuống có kiểm soát."),
    (r"^squeeze your shoulder blades at the top\.?$", "Ép hai bả vai lại với nhau ở vị trí trên cùng."),
    (r"^drive your hips forward to return to standing\.?$", "Đẩy hông về phía trước để đứng thẳng trở lại."),
    (r"^stand holding dumbbells at your sides\.?$", "Đứng thẳng, giữ tạ đơn ở hai bên thân người."),
    (r"^grip the bar slightly wider than shoulder-width\.?$", "Nắm thanh tạ rộng hơn vai một chút."),
    (r"^slowly return to the starting position\.?$", "Từ từ trở về vị trí ban đầu."),
    (r"^lower the bar to your upper chest\.?$", "Hạ thanh tạ xuống vùng ngực trên có kiểm soát."),
    (r"^press back up to the starting position\.?$", "Đẩy trở lại vị trí ban đầu."),
    (r"^return to the starting position with control\.?$", "Trở về vị trí ban đầu một cách có kiểm soát."),
    (r"^hold briefly at the top\.?$", "Giữ ngắn ở vị trí trên cùng."),
    (r"^lower your body by bending your elbows until shoulders are below elbows\.?$", "Gập khuỷu tay để hạ người xuống đến khi vai thấp hơn khuỷu tay."),
    (r"^drive your hips up by squeezing your glutes\.?$", "Siết mông và đẩy hông lên cao."),
    (r"^place a barbell across your upper back and stand tall\.?$", "Đặt thanh tạ ngang lưng trên và đứng thẳng người."),
    (r"^step forward with one leg into a long stride\.?$", "Bước một chân dài về phía trước để vào tư thế lunge."),
    (r"^shrug your shoulders straight up toward your ears\.?$", "Nhún vai thẳng lên về phía tai."),
    (r"^kneel on the floor in front of a bench\.?$", "Quỳ trên sàn phía trước ghế tập."),
    (r"^squeeze your calves at the top\.?$", "Siết bắp chân ở vị trí trên cùng."),
    (r"^lower your head toward the floor by bending your elbows\.?$", "Gập khuỷu tay để hạ đầu xuống gần sàn có kiểm soát."),
    (r"^drive through your heels to return to standing\.?$", "Đạp qua gót chân để đứng thẳng trở lại."),
    (r"^stand with feet shoulder-width apart\.?$", "Đứng hai chân rộng bằng vai."),
    (r"^lower with control and repeat\.?$", "Hạ xuống có kiểm soát rồi lặp lại."),
    (r"^return under control and repeat\.?$", "Trở về có kiểm soát rồi lặp lại."),
    (r"^return under control\. complete reps on one side, then switch\.?$", "Trở về có kiểm soát, hoàn thành một bên rồi đổi bên."),
    (r"^complete all reps on one side before switching\.?$", "Hoàn thành toàn bộ số lần ở một bên trước khi đổi bên."),
    (r"^position yourself in the captain's chair with your back flat against the pad and forearms on the armrests\.?$", "Vào ghế captain chair, ép lưng sát đệm và đặt cẳng tay lên tay tựa."),
    (r"^let your legs hang straight down\.?$", "Để hai chân duỗi thẳng xuống dưới."),
    (r"^engage your core and raise your knees toward your chest\.?$", "Siết cơ bụng và nâng gối về phía ngực."),
    (r"^hold the position for the desired duration\.?$", "Giữ tư thế trong thời lượng được chỉ định."),
    (r"^press back up\.?$", "Đẩy người trở lại vị trí trên cùng."),
    (r"^squeeze your lats at the bottom\.?$", "Siết cơ xô ở cuối chuyển động."),
    (r"^squeeze your abs at the top\.?$", "Siết cơ bụng ở vị trí trên cùng."),
    (r"^set the bench to a decline angle\. lie down and secure your feet\.?$", "Điều chỉnh ghế dốc xuống, nằm lên ghế và cố định hai chân."),
    (r"^press back up to extend your arms\.?$", "Đẩy lên để duỗi tay trở lại."),
    (r"^set two kettlebells on the floor between your feet\.?$", "Đặt hai tạ chuông trên sàn giữa hai chân."),
    (r"^recover by stepping feet back together\.?$", "Bước chân về lại gần nhau để trở về tư thế chuẩn bị."),
    (r"^clean two kettlebells to the rack position at your shoulders\.?$", "Đưa hai tạ chuông lên vị trí giữ ngang vai."),
    (r"^lower yourself under control until arms are fully extended\.?$", "Hạ người xuống có kiểm soát đến khi hai tay duỗi gần thẳng."),
    (r"^lock out your arms at the top\.?$", "Duỗi tay ở vị trí trên cùng nhưng vẫn giữ kiểm soát khớp."),
    (r"^let your arms hang straight down from your shoulders\.?$", "Để hai tay duỗi thẳng xuống từ vai."),
    (r"^drive through your heels to stand back up\.?$", "Đạp qua gót chân để đứng lên trở lại."),
    (r"^pull the bar straight up along your body toward your chin\.?$", "Kéo thanh tạ thẳng dọc thân người lên gần cằm."),
    (r"^lead with your elbows, keeping them above your hands\.?$", "Dẫn chuyển động bằng khuỷu tay và giữ khuỷu tay cao hơn bàn tay."),
    (r"^drive back up\.?$", "Đẩy người lên trở lại."),
    (r"^lower your hips back down with control\.?$", "Hạ hông xuống có kiểm soát."),
    (r"^brace your core and set your back flat\.?$", "Siết cơ bụng và giữ lưng phẳng, trung lập."),
    (r"^lock out at the top with shoulders pulled back\.?$", "Duỗi người ở vị trí trên cùng và kéo vai nhẹ về sau."),
    (r"^keep your body in a straight line from head to heels\.?$", "Giữ cơ thể thành một đường thẳng từ đầu đến gót chân."),
    (r"^lower slowly\.?$", "Hạ xuống chậm rãi và có kiểm soát."),
    (r"^push back up to the starting position\.?$", "Đẩy người trở lại vị trí ban đầu."),
    (r"^drive through your standing heel to return to standing\.?$", "Đạp qua gót chân trụ để đứng thẳng trở lại."),
    (r"^slowly return the bar to the starting position\.?$", "Từ từ đưa thanh tạ về vị trí ban đầu."),
    (r"^extend your arms back to the starting position\.?$", "Duỗi tay trở lại vị trí ban đầu."),
    (r"^hold the position\.?$", "Giữ nguyên tư thế trong thời gian được chỉ định."),
    (r"^brace the core hard so the lower back stays neutral\.?$", "Siết chặt cơ bụng để giữ lưng dưới ở vị trí trung lập."),
    (r"^keep your core tight and body in a straight line\.?$", "Giữ thân giữa chắc và cơ thể tạo thành một đường thẳng."),
    (r"^step onto the assisted dip machine with knees on the pad\.?$", "Bước lên máy hỗ trợ dip và đặt gối lên đệm."),
    (r"^grip the parallel bars and support your weight with straight arms\.?$", "Nắm hai thanh song song và chống người với hai tay gần duỗi thẳng."),
    (r"^loop a resistance band over the pull-up bar and step one foot into it\.?$", "Vòng dây kháng lực qua thanh xà và đặt một chân vào dây."),
    (r"^grip the bar with palms facing away, shoulder-width apart\.?$", "Nắm thanh xà rộng bằng vai, lòng bàn tay hướng ra ngoài."),
    (r"^lie on your back with a band looped around one foot\.?$", "Nằm ngửa và vòng dây kháng lực quanh một bàn chân."),
    (r"^raise that leg and let it open out to the side\.?$", "Nâng chân đó lên rồi mở sang một bên có kiểm soát."),
    (r"^hold the band to control how far the leg lowers\.?$", "Giữ dây để kiểm soát biên độ hạ chân."),
    (r"^sit with one leg extended and a band around the forefoot\.?$", "Ngồi duỗi một chân và vòng dây quanh phần trước bàn chân."),
    (r"^hold the band in both hands\.?$", "Giữ dây bằng cả hai tay."),
    (r"^pull so the toes draw back toward your shin\.?$", "Kéo dây để mũi chân hướng về phía ống chân."),
    (r"^lie on your back and loop a band around the ball of one foot\.?$", "Nằm ngửa và vòng dây quanh phần trước lòng bàn chân."),
    (r"^raise the leg and keep it fairly straight\.?$", "Nâng chân lên và giữ chân tương đối thẳng."),
    (r"^pull the band so your toes draw back toward your shin\.?$", "Kéo dây để mũi chân hướng về phía ống chân."),
    (r"^hold a band behind your back with both hands\.?$", "Giữ dây kháng lực phía sau lưng bằng cả hai tay."),
    (r"^straighten your arms and draw them apart\.?$", "Duỗi tay và kéo hai tay tách xa nhau."),
    (r"^lift your chest and squeeze your shoulder blades\.?$", "Nâng ngực và ép hai bả vai lại với nhau."),
    (r"^lie on your back and cross one ankle over the opposite thigh\.?$", "Nằm ngửa và đặt một cổ chân lên đùi bên đối diện."),
    (r"^loop a band around the supporting thigh\.?$", "Vòng dây quanh đùi đang làm điểm tựa."),
    (r"^pull both legs toward your chest with the band\.?$", "Dùng dây kéo hai chân về phía ngực."),
    (r"^lie on your back and loop a band around one foot\.?$", "Nằm ngửa và vòng dây quanh một bàn chân."),
    (r"^raise that leg straight up, holding the band in both hands\.?$", "Nâng chân thẳng lên, giữ dây bằng cả hai tay."),
    (r"^gently pull the band to draw the leg toward you\.?$", "Kéo dây nhẹ nhàng để đưa chân lại gần người."),
    (r"^lie on your back with a band around one raised foot\.?$", "Nằm ngửa, vòng dây quanh một bàn chân đang nâng lên."),
    (r"^hold the band with the opposite hand\.?$", "Giữ dây bằng tay đối diện."),
    (r"^draw the straight leg across your body toward the floor\.?$", "Đưa chân thẳng chéo qua thân người hướng xuống sàn."),
    (r"^hold a band overhead with both hands under light tension\.?$", "Giữ dây phía trên đầu bằng hai tay với lực căng nhẹ."),
    (r"^let your chest sink to lengthen the sides of your back\.?$", "Để ngực hạ xuống nhẹ nhằm kéo giãn hai bên lưng."),
    (r"^draw that arm horizontally across your chest\.?$", "Kéo tay ngang qua trước ngực."),
    (r"^use the band to deepen the pull gently\.?$", "Dùng dây để tăng độ kéo giãn một cách nhẹ nhàng."),
    (r"^hold a band behind your back, one hand high and one low\.?$", "Giữ dây phía sau lưng, một tay ở trên và một tay ở dưới."),
    (r"^keep light tension in the band\.?$", "Giữ dây có độ căng nhẹ."),
    (r"^open your chest and draw your shoulders gently back\.?$", "Mở ngực và kéo vai nhẹ về sau."),
    (r"^hold a band that runs down your back, top hand behind your head\.?$", "Giữ dây chạy dọc sau lưng, tay trên đặt sau đầu."),
    (r"^anchor the lower hand at your lower back\.?$", "Cố định tay dưới ở vùng lưng dưới."),
    (r"^reach the top hand down to feel the triceps lengthen\.?$", "Đưa tay trên xuống để cảm nhận cơ tay sau được kéo giãn."),
    (r"^place a barbell across your upper back as in a squat\.?$", "Đặt thanh tạ ngang lưng trên như tư thế squat."),
    (r"^stand with the balls of your feet on a raised platform\.?$", "Đứng bằng phần trước bàn chân trên bục nâng."),
    (r"^push up onto your toes as high as possible\.?$", "Nhón lên mũi chân cao nhất có thể."),
    (r"^lower your heels below the platform and repeat\.?$", "Hạ gót chân xuống thấp hơn mặt bục rồi lặp lại."),
    (r"^stand holding a barbell with a shoulder-width underhand grip\.?$", "Đứng thẳng, nắm thanh tạ rộng bằng vai với lòng bàn tay hướng lên."),
    (r"^stand holding a barbell with an overhand grip at thigh level\.?$", "Đứng thẳng, nắm thanh tạ sấp ở ngang đùi."),
    (r"^keep your arms straight and core braced\.?$", "Giữ tay gần duỗi thẳng và siết cơ bụng."),
    (r"^raise the barbell in front of you to shoulder height\.?$", "Nâng thanh tạ ra trước đến ngang vai."),
    (r"^lie on the floor with a barbell across your hips and knees bent\.?$", "Nằm trên sàn, đặt thanh tạ ngang hông và gập gối."),
    (r"^hold at the top with hips fully extended\.?$", "Giữ ở vị trí trên cùng khi hông đã duỗi hoàn toàn."),
    (r"^lower your back knee toward the ground until your front thigh is parallel\.?$", "Hạ gối sau về phía sàn đến khi đùi trước gần song song mặt đất."),
    (r"^lie across a bench with a barbell held over your chest\.?$", "Nằm ngang trên ghế, giữ thanh tạ phía trên ngực."),
    (r"^lower the bar back over your head in an arc\.?$", "Hạ thanh tạ ra sau đầu theo đường vòng cung."),
    (r"^pull it back to the start over your chest\.?$", "Kéo tạ trở lại vị trí ban đầu phía trên ngực."),
    (r"^step one foot backward into a long stride\.?$", "Bước một chân dài ra sau để vào tư thế reverse lunge."),
    (r"^lower your back knee toward the ground under control\.?$", "Hạ gối sau về phía sàn có kiểm soát."),
    (r"^pull the bar to your lower chest, squeezing your shoulder blades\.?$", "Kéo thanh tạ về vùng ngực dưới đồng thời ép hai bả vai lại."),
    (r"^lower the bar under control\.?$", "Hạ thanh tạ xuống có kiểm soát."),
]


def vietnamese_exercise_name(name: str) -> str:
    text = str(name or "")
    replacements = [
        ("Push Ups", "Chống đẩy"),
        ("Push Up", "Chống đẩy"),
        ("Pull Ups", "Kéo xà"),
        ("Pull Up", "Kéo xà"),
        ("Bench Press", "Đẩy ngực trên ghế"),
        ("Chest Press", "Đẩy ngực máy"),
        ("Shoulder Press", "Đẩy vai"),
        ("Curl", "Cuốn tay"),
        ("Squat", "Squat"),
        ("Deadlift", "Deadlift"),
        ("Crunch", "Gập bụng"),
        ("Plank", "Plank"),
        ("Row", "Kéo lưng"),
        ("Dip", "Nhúng xà"),
        ("Dips", "Nhúng xà"),
        ("Calf Raise", "Nhón bắp chân"),
        ("Leg Curl", "Cuốn đùi sau"),
        ("Leg Extension", "Duỗi đùi trước"),
        ("Face Pull", "Kéo mặt"),
    ]
    for src, dst in replacements:
        text = text.replace(src, dst)
    return text


def translate_step(step: str, exercise_name: str = "") -> str:
    raw = str(step or "").strip()
    if not raw:
        return ""
    lowered = raw.lower()
    for pattern, replacement in STEP_PATTERNS:
        if re.match(pattern, lowered):
            return replacement
    translated = raw
    for pattern, replacement in PHRASE_REPLACEMENTS:
        translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)
    if translated != raw and not _has_english_verbs(translated):
        return _polish_sentence(translated)
    return _fallback_step(raw, exercise_name)


def translate_steps(instructions: str, exercise_name: str = "") -> list[str]:
    parts = [part.strip() for part in str(instructions or "").split("|") if part.strip()]
    return [translate_step(part, exercise_name) for part in parts]


def _fallback_step(step: str, exercise_name: str) -> str:
    lowered = step.lower()
    if lowered.startswith(("sit ", "stand ", "lie ", "place ", "set up ", "step ")):
        return "Vào đúng tư thế chuẩn bị theo mô tả bài tập, căn chỉnh thân người và giữ điểm tựa vững trước khi bắt đầu."
    if lowered.startswith(("grip ", "grab ", "hold ")):
        return "Giữ chắc điểm tựa hoặc dụng cụ, để cổ tay thẳng tự nhiên và ổn định vai trước khi chuyển động."
    if lowered.startswith(("pull ", "row ")):
        return "Kéo theo đúng đường chuyển động, siết cơ mục tiêu ở cuối pha kéo và tránh giật người lấy đà."
    if lowered.startswith(("press ", "push ")):
        return "Đẩy theo đường chuyển động ổn định, kiểm soát vai/khuỷu tay và không khóa cứng khớp ở cuối pha đẩy."
    if lowered.startswith(("raise ", "lift ")):
        return "Nâng theo biên độ phù hợp, giữ thân người chắc và tránh vung người để lấy đà."
    if lowered.startswith(("lower ", "return ")):
        return "Hạ xuống hoặc trở về vị trí ban đầu chậm rãi, giữ kiểm soát trong toàn bộ pha âm."
    if lowered.startswith(("drive ", "extend ", "curl ", "shrug ", "squeeze ")):
        return "Thực hiện pha chính của động tác với lực đều, cảm nhận nhóm cơ mục tiêu làm việc và giữ nhịp thở ổn định."
    if lowered.startswith(("hinge ", "bend ")):
        return "Gập hông hoặc gập người trong biên độ an toàn, giữ lưng trung lập và kiểm soát thân người."
    if lowered.startswith(("walk ", "continue ")):
        return "Tiếp tục thực hiện trong thời lượng hoặc quãng đường được chỉ định, duy trì nhịp thở đều."
    if lowered.startswith(("pause ", "hold ")) or "hold" in lowered:
        return "Giữ vị trí theo thời gian yêu cầu, duy trì căng cơ vừa phải và thở đều."
    if lowered.startswith(("switch ", "alternate ")):
        return "Đổi bên hoặc luân phiên hai bên theo số lần được chỉ định."
    if lowered.startswith(("repeat ", "complete ")):
        return "Hoàn thành đủ số lần lặp được chỉ định với kỹ thuật ổn định."
    return "Thực hiện đúng ý của bước này theo nhịp kiểm soát, ưu tiên biên độ an toàn và cảm giác cơ mục tiêu."


def _polish_sentence(text: str) -> str:
    text = text.strip()
    text = text[0].upper() + text[1:] if text else text
    return text if text.endswith(".") else text + "."


def _has_english_verbs(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "grip ", "hold ", "pull ", "push ", "press ", "lower ", "raise ",
        "place ", "sit ", "stand ", "lie ", "step ", "drive ", "loop ",
        " and ", " for the ", " with ", " your ", " barbell", " dumbbell",
        " cable", " bench", " kettlebell", " machine",
    ]
    return any(marker in lowered for marker in markers)
